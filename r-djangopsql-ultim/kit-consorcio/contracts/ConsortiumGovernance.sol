// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// @title ConsortiumGovernance
/// @notice Federated membership shared by D2 (proposed contract) and D3 (plain registry), so that
///         the difference between them isolates the ERC-721 / ERC-5192 layer.
///         - Admission: four fifths of the active members (4 of 5), so a coalition that cannot suspend
///           a member cannot add members either (no capture through phantom admissions).
///         - Suspension: four fifths of the active members other than the target, who cannot vote on
///           it (4 of the other 4 in a five-campus consortium). It confirms any emergency declaration
///           against the campus and may itself declare the campus compromised since a given time.
///         - Emergency revocation: a simple majority of the members other than the target (3 of the
///           other 4) may declare a campus compromised since a time at most 7 days in the past. The
///           campus's certificates issued from then on stop verifying at once. The declaration is
///           provisional: it lapses after 14 days unless a suspension confirms it, so a single silent
///           member cannot block an emergency and three colluding campuses cannot invalidate a fourth
///           campus's certificates for good.
///         - Readmission: simple majority (3 of 5).
///         - Certificate renewal: proposed only by the campus itself and approved by a simple majority
///           (3 of 5, the proposer included), so no coalition can replace another campus's certificate.
///           A renewal ends any open compromise period of the campus.
///         - Each campus is bound to the SHA-256 fingerprint of the X.509 certificate that signs its
///           PDFs; the history of fingerprints is kept so a verifier can check the signer of an old
///           document against the certificate that was registered when it was issued.
///         The proposer's vote counts as yes.
abstract contract ConsortiumGovernance {
    enum ProposalKind { Admit, Suspend, Readmit, RotateCert, DeclareCompromise }

    uint64 public constant MAX_BACKDATE = 7 days;
    uint64 public constant PROVISIONAL_PERIOD = 14 days;

    struct Member {
        bool exists;
        bool active;
        uint8 campusId;
    }

    struct Proposal {
        ProposalKind kind;
        address target;
        uint8 campusId;
        uint8 yesVotes;
        bool executed;
        uint64 createdAt;
        bytes32 data; // Admit / RotateCert: certificate fingerprint; Suspend / DeclareCompromise: compromised-since time
    }

    struct SigningCert {
        bytes32 fingerprint;
        uint64 validFrom;
    }

    struct Compromise {
        uint64 since; // first issuance time affected
        uint64 until; // 0 = open; set when the campus renews its certificate
        uint64 declaredAt;
        bool confirmed; // confirmed by a suspension; otherwise lapses after PROVISIONAL_PERIOD
    }

    mapping(address => Member) public members;
    mapping(uint8 => address) public campusAccount;
    mapping(uint8 => SigningCert[]) private _certHistory;
    mapping(uint8 => Compromise[]) private _compromises;
    uint8 public activeMembers;

    Proposal[] public proposals;
    mapping(uint256 => mapping(address => bool)) public hasVoted;

    event MemberAdmitted(address indexed account, uint8 indexed campusId);
    event MemberSuspended(address indexed account, uint8 indexed campusId);
    event MemberReadmitted(address indexed account, uint8 indexed campusId);
    event CampusCompromised(uint8 indexed campusId, uint64 since, bool confirmed);
    event SigningCertRegistered(uint8 indexed campusId, bytes32 fingerprint, uint64 validFrom);
    event ProposalCreated(uint256 indexed proposalId, ProposalKind kind, address indexed target, uint8 campusId);
    event VoteCast(uint256 indexed proposalId, address indexed voter);

    error NotActiveMember();
    error InvalidCampus();
    error InvalidTarget();
    error InvalidData();
    error AlreadyVoted();
    error ProposalClosed();
    error StaleProposal();

    modifier onlyActiveMember() {
        if (!members[msg.sender].active) revert NotActiveMember();
        _;
    }

    constructor(address[] memory accounts, uint8[] memory campusIds, bytes32[] memory certFingerprints) {
        if (accounts.length != campusIds.length || accounts.length != certFingerprints.length || accounts.length == 0) {
            revert InvalidTarget();
        }
        for (uint256 i = 0; i < accounts.length; i++) {
            _admit(accounts[i], campusIds[i], certFingerprints[i]);
        }
    }

    function proposalCount() external view returns (uint256) {
        return proposals.length;
    }

    /// @notice Any active member may propose; the proposal counts the proposer's vote.
    function propose(ProposalKind kind, address target, uint8 campusId, bytes32 data)
        external
        onlyActiveMember
        returns (uint256 id)
    {
        _checkProposal(kind, target, campusId, data);
        id = proposals.length;
        proposals.push(Proposal(kind, target, campusId, 0, false, uint64(block.timestamp), data));
        emit ProposalCreated(id, kind, target, campusId);
        _castVote(id);
    }

    function _checkProposal(ProposalKind kind, address target, uint8 campusId, bytes32 data) private view {
        if (kind == ProposalKind.Admit) _checkAdmit(target, campusId, data);
        else if (kind == ProposalKind.Readmit) _checkReadmit(target);
        else if (kind == ProposalKind.RotateCert) _checkRotate(target, data);
        else _checkAgainst(kind, target, data);
    }

    function _checkAdmit(address target, uint8 campusId, bytes32 data) private view {
        if (members[target].exists || target == address(0)) revert InvalidTarget();
        if (campusId == 0 || campusAccount[campusId] != address(0)) revert InvalidCampus();
        if (data == bytes32(0)) revert InvalidData();
    }

    function _checkReadmit(address target) private view {
        Member memory m = members[target];
        if (!m.exists || m.active) revert InvalidTarget();
    }

    /// @dev Only the campus itself renews its certificate, so no coalition can replace another campus's.
    function _checkRotate(address target, bytes32 data) private view {
        if (target != msg.sender) revert InvalidTarget();
        if (data == bytes32(0)) revert InvalidData();
    }

    /// @dev Suspension and emergency declaration: never against oneself; a declaration needs a valid start.
    function _checkAgainst(ProposalKind kind, address target, bytes32 data) private view {
        Member memory m = members[target];
        if (target == msg.sender) revert InvalidTarget();
        if (kind == ProposalKind.Suspend) {
            if (!m.active) revert InvalidTarget();
            if (data != bytes32(0)) _checkCompromiseTime(uint256(data));
        } else {
            if (!m.exists) revert InvalidTarget();
            _checkCompromiseTime(uint256(data));
        }
    }

    /// @dev The compromise start must lie in the past, at most MAX_BACKDATE before now.
    function _checkCompromiseTime(uint256 since) private view {
        if (since == 0 || since > block.timestamp || since + MAX_BACKDATE < block.timestamp) revert InvalidData();
    }

    function vote(uint256 id) external onlyActiveMember {
        _castVote(id);
    }

    /// @notice Fingerprint of the signing certificate registered for a campus at a given time.
    function signingCertAt(uint8 campusId, uint64 at) public view returns (bytes32 fingerprint) {
        SigningCert[] storage hist = _certHistory[campusId];
        for (uint256 i = hist.length; i > 0; i--) {
            if (hist[i - 1].validFrom <= at) return hist[i - 1].fingerprint;
        }
        return bytes32(0);
    }

    function compromiseCount(uint8 campusId) external view returns (uint256) {
        return _compromises[campusId].length;
    }

    function compromiseAt(uint8 campusId, uint256 i) external view returns (Compromise memory) {
        return _compromises[campusId][i];
    }

    function _castVote(uint256 id) private {
        Proposal storage p = proposals[id];
        if (p.executed) revert ProposalClosed();
        if (hasVoted[id][msg.sender]) revert AlreadyVoted();
        bool againstTarget = p.kind == ProposalKind.Suspend || p.kind == ProposalKind.DeclareCompromise;
        if (againstTarget && p.target == msg.sender) revert InvalidTarget();
        _checkStillApplicable(p);
        hasVoted[id][msg.sender] = true;
        p.yesVotes += 1;
        emit VoteCast(id, msg.sender);

        if (!_passed(p)) return;
        p.executed = true;
        _execute(p);
    }

    /// @dev A proposal whose target is no longer in the required state (e.g. a second suspension of a campus that
    ///      another proposal already suspended) cannot collect votes, so it can never execute twice.
    function _checkStillApplicable(Proposal storage p) private view {
        Member memory m = members[p.target];
        bool ok;
        if (p.kind == ProposalKind.Admit) ok = !m.exists && campusAccount[p.campusId] == address(0);
        else if (p.kind == ProposalKind.Readmit) ok = m.exists && !m.active;
        else if (p.kind == ProposalKind.DeclareCompromise) ok = m.exists;
        else ok = m.active; // Suspend, RotateCert
        if (!ok) revert StaleProposal();
    }

    function _passed(Proposal storage p) private view returns (bool) {
        uint256 yes = p.yesVotes;
        uint256 active = activeMembers;
        if (p.kind == ProposalKind.Admit) return yes * 5 >= active * 4;
        if (p.kind == ProposalKind.Suspend) return yes * 5 >= (active - 1) * 4;
        if (p.kind == ProposalKind.DeclareCompromise) {
            uint256 others = members[p.target].active ? active - 1 : active;
            return yes * 2 > others;
        }
        return yes * 2 > active;
    }

    function _execute(Proposal storage p) private {
        uint8 campus = members[p.target].campusId;
        if (p.kind == ProposalKind.Admit) {
            _admit(p.target, p.campusId, p.data);
        } else if (p.kind == ProposalKind.Suspend) {
            members[p.target].active = false;
            activeMembers -= 1;
            emit MemberSuspended(p.target, campus);
            Compromise[] storage list = _compromises[campus];
            for (uint256 i = 0; i < list.length; i++) {
                if (!list[i].confirmed && list[i].until == 0) list[i].confirmed = true;
            }
            if (p.data != bytes32(0)) _declare(campus, uint64(uint256(p.data)), true);
        } else if (p.kind == ProposalKind.Readmit) {
            members[p.target].active = true;
            activeMembers += 1;
            emit MemberReadmitted(p.target, campus);
        } else if (p.kind == ProposalKind.RotateCert) {
            Compromise[] storage open = _compromises[campus];
            for (uint256 i = 0; i < open.length; i++) {
                if (open[i].until == 0) open[i].until = uint64(block.timestamp);
            }
            _registerCert(campus, p.data);
        } else {
            _declare(campus, uint64(uint256(p.data)), false);
        }
    }

    /// @dev A declaration that executes late never reaches further back than MAX_BACKDATE from its execution.
    function _declare(uint8 campus, uint64 since, bool confirmed) private {
        uint64 earliest = uint64(block.timestamp) - MAX_BACKDATE;
        if (since < earliest) since = earliest;
        _compromises[campus].push(Compromise(since, 0, uint64(block.timestamp), confirmed));
        emit CampusCompromised(campus, since, confirmed);
    }

    function _admit(address account, uint8 campusId, bytes32 certFingerprint) private {
        if (account == address(0) || members[account].exists) revert InvalidTarget();
        if (campusId == 0 || campusAccount[campusId] != address(0)) revert InvalidCampus();
        if (certFingerprint == bytes32(0)) revert InvalidData();
        members[account] = Member(true, true, campusId);
        campusAccount[campusId] = account;
        activeMembers += 1;
        _registerCert(campusId, certFingerprint);
        emit MemberAdmitted(account, campusId);
    }

    function _registerCert(uint8 campusId, bytes32 fingerprint) private {
        _certHistory[campusId].push(SigningCert(fingerprint, uint64(block.timestamp)));
        emit SigningCertRegistered(campusId, fingerprint, uint64(block.timestamp));
    }

    function _isActiveCampus(uint8 campusId) internal view returns (bool) {
        address a = campusAccount[campusId];
        return a != address(0) && members[a].active;
    }

    /// @dev A certificate stops verifying if it was issued inside a compromise period of its campus that is
    ///      confirmed, or provisional and not yet lapsed.
    function _issuedWhileCompromised(uint8 campusId, uint64 issuedAt) internal view returns (bool) {
        Compromise[] storage list = _compromises[campusId];
        for (uint256 i = 0; i < list.length; i++) {
            Compromise storage c = list[i];
            bool inPeriod = issuedAt >= c.since && (c.until == 0 || issuedAt < c.until);
            bool inForce = c.confirmed || block.timestamp < uint256(c.declaredAt) + PROVISIONAL_PERIOD;
            if (inPeriod && inForce) return true;
        }
        return false;
    }
}
