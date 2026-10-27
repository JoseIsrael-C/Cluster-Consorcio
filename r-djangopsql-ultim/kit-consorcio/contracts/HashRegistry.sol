// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {ConsortiumGovernance} from "./ConsortiumGovernance.sol";

/// @title D3 · HashRegistry (baseline without tokens)
/// @notice Same data model, membership and governance as D2 but no ERC-721/ERC-5192 layer,
///         so D2 − D3 isolates the cost of the token layer.
contract HashRegistry is ConsortiumGovernance {
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
    event TransferRecorded(uint256 indexed id, uint8 fromCampus, uint8 toCampus);

    error HashAlreadyRegistered();
    error UnknownCertificate();
    error NotIssuer();
    error NotCurrentCampus();
    error AlreadyInvalid();

    constructor(address[] memory accounts, uint8[] memory campusIds, bytes32[] memory certFingerprints)
        ConsortiumGovernance(accounts, campusIds, certFingerprints)
    {}

    function issue(bytes32 h, uint8 docType) external onlyActiveMember returns (uint256 id) {
        if (idByHash[h] != 0) revert HashAlreadyRegistered();
        uint8 c = members[msg.sender].campusId;
        id = _nextId++;
        _certs[id] = Certificate(h, uint64(block.timestamp), docType, c, c, true, 0);
        idByHash[h] = id;
        emit CertificateIssued(id, h, c);
    }

    function revoke(uint256 id) external onlyActiveMember {
        Certificate storage c = _certs[id];
        if (c.docHash == bytes32(0)) revert UnknownCertificate();
        if (c.issuingCampus != members[msg.sender].campusId) revert NotIssuer();
        if (!c.valid) revert AlreadyInvalid();
        c.valid = false;
        emit CertificateRevoked(id, c.issuingCampus);
    }

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
}
