// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {IERC5192} from "./IERC5192.sol";
import {ConsortiumGovernance} from "./ConsortiumGovernance.sol";

/// @title D2 · CertificateConsortium (proposed design, Listing 1)
/// @notice Soulbound ERC-721/ERC-5192 certificates jointly issued by a federation of campuses.
///         Only keccak256(signed PDF) and non-personal metadata are stored on-chain.
contract CertificateConsortium is ERC721, IERC5192, ConsortiumGovernance {
    struct Certificate {
        bytes32 docHash;
        uint64 issuedAt;
        uint8 docType;
        uint8 issuingCampus;
        uint8 currentCampus;
        bool valid;
        uint256 replacesId;
    }

    uint256 private _nextId = 1;
    mapping(uint256 => Certificate) private _certs;
    mapping(bytes32 => uint256) public idByHash;

    event CertificateIssued(uint256 indexed id, bytes32 indexed docHash, uint8 indexed campus);
    event CertificateRevoked(uint256 indexed id, uint8 indexed campus);
    event CertificateReissued(uint256 indexed oldId, uint256 indexed newId, bytes32 newHash);
    event TransferRecorded(uint256 indexed id, uint8 fromCampus, uint8 toCampus);

    error HashAlreadyRegistered();
    error UnknownCertificate();
    error NotIssuer();
    error NotCurrentCampus();
    error AlreadyInvalid();
    error Soulbound();

    constructor(address[] memory accounts, uint8[] memory campusIds, bytes32[] memory certFingerprints)
        ERC721("Academic Certificate Consortium", "ACC")
        ConsortiumGovernance(accounts, campusIds, certFingerprints)
    {}

    function issue(bytes32 h, uint8 docType) external onlyActiveMember returns (uint256 id) {
        id = _issue(h, docType, 0, members[msg.sender].campusId);
    }

    /// @notice Revocation keeps the token and its history; only the issuing campus may revoke.
    function revoke(uint256 id) external onlyActiveMember {
        Certificate storage c = _issuerCert(id);
        c.valid = false;
        emit CertificateRevoked(id, c.issuingCampus);
    }

    /// @notice Corrected certificate: the old token becomes invalid and the new one points to it.
    function reissue(uint256 oldId, bytes32 newHash, uint8 docType)
        external
        onlyActiveMember
        returns (uint256 newId)
    {
        Certificate storage old = _issuerCert(oldId);
        old.valid = false;
        emit CertificateRevoked(oldId, old.issuingCampus);
        newId = _issue(newHash, docType, oldId, old.currentCampus);
        emit CertificateReissued(oldId, newId, newHash);
    }

    /// @notice Records a student transfer; only the campus where the student is enrolled may call it.
    function recordTransfer(uint256 id, uint8 toCampus) external onlyActiveMember {
        Certificate storage c = _certs[id];
        if (c.docHash == bytes32(0)) revert UnknownCertificate();
        if (!c.valid) revert AlreadyInvalid();
        uint8 from = c.currentCampus;
        if (members[msg.sender].campusId != from) revert NotCurrentCampus();
        if (toCampus == from || !_isActiveCampus(toCampus)) revert InvalidCampus();
        c.currentCampus = toCampus;
        emit TransferRecorded(id, from, toCampus);
    }

    /// @notice Validity also requires that the issuing campus was not declared compromised at issuance time.
    ///         The verifier must additionally check that the PDF is signed by the certificate registered
    ///         for the issuing campus at that time (signingCertAt).
    function verify(bytes32 h)
        external
        view
        returns (bool valid, uint256 id, uint8 issuer, uint8 current, uint64 at)
    {
        id = idByHash[h];
        if (id == 0) return (false, 0, 0, 0, 0);
        Certificate storage c = _certs[id];
        bool ok = c.valid && !_issuedWhileCompromised(c.issuingCampus, c.issuedAt);
        return (ok, id, c.issuingCampus, c.currentCampus, c.issuedAt);
    }

    /// @notice Full on-chain record of a certificate (every issued certificate is a minted token).
    function certificate(uint256 id) external view returns (Certificate memory) {
        _requireOwned(id);
        return _certs[id];
    }

    /// @inheritdoc IERC5192
    function locked(uint256 id) external view returns (bool) {
        _requireOwned(id);
        return true;
    }

    function supportsInterface(bytes4 interfaceId) public view override returns (bool) {
        return interfaceId == type(IERC5192).interfaceId || super.supportsInterface(interfaceId);
    }

    function _issue(bytes32 h, uint8 docType, uint256 replacesId, uint8 currentCampus)
        private
        returns (uint256 id)
    {
        if (idByHash[h] != 0) revert HashAlreadyRegistered();
        uint8 c = members[msg.sender].campusId;
        id = _nextId++;
        _certs[id] = Certificate(h, uint64(block.timestamp), docType, c, currentCampus, true, replacesId);
        idByHash[h] = id;
        _safeMint(msg.sender, id);
        emit Locked(id);
        emit CertificateIssued(id, h, c);
    }

    function _issuerCert(uint256 id) private view returns (Certificate storage c) {
        c = _certs[id];
        if (c.docHash == bytes32(0)) revert UnknownCertificate();
        if (c.issuingCampus != members[msg.sender].campusId) revert NotIssuer();
        if (!c.valid) revert AlreadyInvalid();
    }

    /// @dev Soulbound: every movement except minting reverts.
    function _update(address to, uint256 id, address auth) internal override returns (address) {
        if (_ownerOf(id) != address(0)) revert Soulbound();
        return super._update(to, id, auth);
    }
}
