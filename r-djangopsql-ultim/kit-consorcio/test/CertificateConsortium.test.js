// Functional and security tests T1–T17 (Table 5 of the paper). Run: npx hardhat test
const { expect } = require("chai");
const { ethers } = require("hardhat");
const { loadFixture } = require("@nomicfoundation/hardhat-toolbox/network-helpers");

const h = (s) => ethers.keccak256(ethers.toUtf8Bytes(s));
const ADMIT = 0;
const SUSPEND = 1;
const READMIT = 2;
const ROTATE = 3;
const COMPROMISE = 4;
const DAY = 24 * 3600;
const now = async () => BigInt((await ethers.provider.getBlock("latest")).timestamp);
const hex = (t) => ethers.toBeHex(t, 32);
const Z = ethers.ZeroHash;
const fp = (i) => ethers.keccak256(ethers.toUtf8Bytes(`x509-campus-${i}`)); // stands in for SHA-256 of the DER certificate

async function deployConsortium() {
  const [c1, c2, c3, c4, c5, outsider, newcomer] = await ethers.getSigners();
  const founders = [c1, c2, c3, c4, c5];
  const cc = await ethers.deployContract("CertificateConsortium", [founders.map((s) => s.address), [1, 2, 3, 4, 5], [1, 2, 3, 4, 5].map(fp)]);
  return { cc, c1, c2, c3, c4, c5, outsider, newcomer };
}

describe("CertificateConsortium (D2) · T1–T17", function () {
  it("T1 access control: a non-member cannot issue", async function () {
    const { cc, outsider } = await loadFixture(deployConsortium);
    await expect(cc.connect(outsider).issue(h("pdf-1"), 1)).to.be.revertedWithCustomError(cc, "NotActiveMember");
  });

  it("T2 integrity: verify by hash returns validity, issuer and current campus", async function () {
    const { cc, c1 } = await loadFixture(deployConsortium);
    await expect(cc.connect(c1).issue(h("pdf-1"), 1)).to.emit(cc, "CertificateIssued").withArgs(1n, h("pdf-1"), 1n);
    const [valid, id, issuer, current, at] = await cc.verify(h("pdf-1"));
    expect([valid, id, issuer, current]).to.deep.equal([true, 1n, 1n, 1n]);
    expect(at).to.be.greaterThan(0n);
    const [v2, id2] = await cc.verify(h("unknown-pdf"));
    expect([v2, id2]).to.deep.equal([false, 0n]);
  });

  it("T3 integrity: a duplicate hash is rejected, also from another campus", async function () {
    const { cc, c1, c2 } = await loadFixture(deployConsortium);
    await cc.connect(c1).issue(h("pdf-1"), 1);
    await expect(cc.connect(c2).issue(h("pdf-1"), 1)).to.be.revertedWithCustomError(cc, "HashAlreadyRegistered");
  });

  it("T4 soulbound: transfers revert and locked() is true (ERC-5192)", async function () {
    const { cc, c1, c2 } = await loadFixture(deployConsortium);
    await expect(cc.connect(c1).issue(h("pdf-1"), 1)).to.emit(cc, "Locked").withArgs(1n);
    expect(await cc.locked(1)).to.equal(true);
    expect(await cc.supportsInterface("0xb45a3c0e")).to.equal(true);
    expect(await cc.ownerOf(1)).to.equal(c1.address);
    await expect(cc.connect(c1).transferFrom(c1.address, c2.address, 1)).to.be.revertedWithCustomError(cc, "Soulbound");
    await expect(
      cc.connect(c1)["safeTransferFrom(address,address,uint256)"](c1.address, c2.address, 1),
    ).to.be.revertedWithCustomError(cc, "Soulbound");
    expect(await cc.ownerOf(1)).to.equal(c1.address);
  });

  it("T5 revocation: only the issuing campus revokes and history is kept", async function () {
    const { cc, c1, c2 } = await loadFixture(deployConsortium);
    await cc.connect(c1).issue(h("pdf-1"), 1);
    await expect(cc.connect(c2).revoke(1)).to.be.revertedWithCustomError(cc, "NotIssuer");
    await expect(cc.connect(c1).revoke(1)).to.emit(cc, "CertificateRevoked").withArgs(1n, 1n);
    const [valid, id] = await cc.verify(h("pdf-1"));
    expect([valid, id]).to.deep.equal([false, 1n]);
    expect(await cc.ownerOf(1)).to.equal(c1.address);
    await expect(cc.connect(c1).revoke(1)).to.be.revertedWithCustomError(cc, "AlreadyInvalid");
  });

  it("T6 transfers: only the current campus records a transfer", async function () {
    const { cc, c1, c2 } = await loadFixture(deployConsortium);
    await cc.connect(c1).issue(h("pdf-1"), 1);
    await expect(cc.connect(c2).recordTransfer(1, 3)).to.be.revertedWithCustomError(cc, "NotCurrentCampus");
    await expect(cc.connect(c1).recordTransfer(1, 2)).to.emit(cc, "TransferRecorded").withArgs(1n, 1n, 2n);
    expect((await cc.verify(h("pdf-1")))[3]).to.equal(2n);
    await expect(cc.connect(c1).recordTransfer(1, 3)).to.be.revertedWithCustomError(cc, "NotCurrentCampus");
    await expect(cc.connect(c2).recordTransfer(1, 9)).to.be.revertedWithCustomError(cc, "InvalidCampus");
    await cc.connect(c2).recordTransfer(1, 3);
    const [, , issuer, current] = await cc.verify(h("pdf-1"));
    expect([issuer, current]).to.deep.equal([1n, 3n]);
  });

  it("T7 re-issue: issuer only; the new token links to the superseded one", async function () {
    const { cc, c1, c2 } = await loadFixture(deployConsortium);
    await cc.connect(c1).issue(h("pdf-1"), 1);
    await expect(cc.connect(c2).reissue(1, h("pdf-1-corrected"), 1)).to.be.revertedWithCustomError(cc, "NotIssuer");
    await expect(cc.connect(c1).reissue(1, h("pdf-1-corrected"), 1))
      .to.emit(cc, "CertificateReissued")
      .withArgs(1n, 2n, h("pdf-1-corrected"));
    expect((await cc.verify(h("pdf-1")))[0]).to.equal(false);
    expect((await cc.verify(h("pdf-1-corrected")))[0]).to.equal(true);
    expect((await cc.certificate(2)).replacesId).to.equal(1n);
  });

  it("T8 governance: admission needs four fifths (4 of 5), so three campuses cannot admit members", async function () {
    const { cc, c1, c2, c3, c4, newcomer } = await loadFixture(deployConsortium);
    await cc.connect(c1).propose(ADMIT, newcomer.address, 6, fp(6));
    await cc.connect(c2).vote(0);
    await cc.connect(c3).vote(0);
    expect((await cc.members(newcomer.address)).active).to.equal(false); // a coalition of three is not enough
    await expect(cc.connect(c4).vote(0)).to.emit(cc, "MemberAdmitted").withArgs(newcomer.address, 6n);
    expect(await cc.activeMembers()).to.equal(6n);
    expect(await cc.signingCertAt(6, 2n ** 63n)).to.equal(fp(6));
    await expect(cc.connect(newcomer).issue(h("pdf-6"), 1)).to.emit(cc, "CertificateIssued");
  });

  it("T9 governance: suspension needs four fifths of the other members (three campuses cannot expel)", async function () {
    const { cc, c1, c2, c3, c4, c5 } = await loadFixture(deployConsortium);
    await cc.connect(c1).propose(SUSPEND, c5.address, 0, Z);
    await cc.connect(c2).vote(0);
    await cc.connect(c3).vote(0);
    expect((await cc.members(c5.address)).active).to.equal(true);
    await expect(cc.connect(c5).vote(0)).to.be.revertedWithCustomError(cc, "InvalidTarget");
    await expect(cc.connect(c4).vote(0)).to.emit(cc, "MemberSuspended").withArgs(c5.address, 5n);
    expect(await cc.activeMembers()).to.equal(4n);
    await expect(cc.connect(c5).issue(h("pdf-5"), 1)).to.be.revertedWithCustomError(cc, "NotActiveMember");
    // with four active members, a further suspension needs all three other members (four fifths of 3)
    await cc.connect(c1).propose(SUSPEND, c4.address, 0, Z);
    await cc.connect(c2).vote(1);
    expect((await cc.members(c4.address)).active).to.equal(true);
    await expect(cc.connect(c3).vote(1)).to.emit(cc, "MemberSuspended").withArgs(c4.address, 4n);
    expect(await cc.activeMembers()).to.equal(3n);
  });

  it("T10 governance: a suspended campus is readmitted by simple majority", async function () {
    const { cc, c1, c2, c3, c4, c5 } = await loadFixture(deployConsortium);
    await cc.connect(c1).propose(SUSPEND, c5.address, 0, Z);
    for (const s of [c2, c3, c4]) await cc.connect(s).vote(0);
    await cc.connect(c1).propose(READMIT, c5.address, 0, Z);
    await cc.connect(c2).vote(1);
    expect((await cc.members(c5.address)).active).to.equal(false);
    await expect(cc.connect(c3).vote(1)).to.emit(cc, "MemberReadmitted").withArgs(c5.address, 5n);
    expect(await cc.activeMembers()).to.equal(5n);
    await expect(cc.connect(c5).issue(h("pdf-5"), 1)).to.emit(cc, "CertificateIssued");
  });

  it("T11 access control: non-members cannot propose or vote; no double voting", async function () {
    const { cc, c1, outsider, newcomer } = await loadFixture(deployConsortium);
    await expect(cc.connect(outsider).propose(ADMIT, newcomer.address, 6, fp(6))).to.be.revertedWithCustomError(
      cc,
      "NotActiveMember",
    );
    await cc.connect(c1).propose(ADMIT, newcomer.address, 6, fp(6));
    await expect(cc.connect(outsider).vote(0)).to.be.revertedWithCustomError(cc, "NotActiveMember");
    await expect(cc.connect(c1).vote(0)).to.be.revertedWithCustomError(cc, "AlreadyVoted");
  });

  it("T12 governance history: certificates issued before a suspension remain verifiable", async function () {
    const { cc, c1, c2, c3, c4, c5 } = await loadFixture(deployConsortium);
    await cc.connect(c5).issue(h("pdf-from-5"), 1);
    await cc.connect(c1).propose(SUSPEND, c5.address, 0, Z);
    for (const s of [c2, c3, c4]) await cc.connect(s).vote(0);
    const [valid, id, issuer] = await cc.verify(h("pdf-from-5"));
    expect([valid, id, issuer]).to.deep.equal([true, 1n, 5n]);
    const p = await cc.proposals(0);
    expect(p.executed).to.equal(true);
    expect(p.yesVotes).to.equal(4n);
    expect(await cc.proposalCount()).to.equal(1n);
    await expect(cc.connect(c2).vote(0)).to.be.revertedWithCustomError(cc, "ProposalClosed");
  });

  it("T13 identity binding: each campus is bound to its signing certificate; only the campus itself renews it", async function () {
    const { cc, c1, c2, c3, c4, outsider } = await loadFixture(deployConsortium);
    // no coalition can replace another campus's certificate
    await expect(cc.connect(c2).propose(ROTATE, c1.address, 0, fp(666))).to.be.revertedWithCustomError(cc, "InvalidTarget");
    await expect(cc.connect(c1).propose(ADMIT, outsider.address, 7, Z)).to.be.revertedWithCustomError(cc, "InvalidData");
    const t0 = BigInt((await ethers.provider.getBlock("latest")).timestamp);
    expect(await cc.signingCertAt(1, t0)).to.equal(fp(1));
    await cc.connect(c1).issue(h("pdf-old-key"), 1);
    const [, , , , issuedOld] = await cc.verify(h("pdf-old-key"));
    await cc.connect(c1).propose(ROTATE, c1.address, 0, fp(101));
    await cc.connect(c2).vote(0);
    expect(await cc.signingCertAt(1, 2n ** 63n)).to.equal(fp(1)); // 2 of 5 is not a majority
    await expect(cc.connect(c3).vote(0)).to.emit(cc, "SigningCertRegistered");
    expect(await cc.signingCertAt(1, 2n ** 63n)).to.equal(fp(101));
    expect(await cc.signingCertAt(1, issuedOld)).to.equal(fp(1)); // old documents are checked against the old certificate
  });

  it("T14 emergency revocation: a majority of the other campuses invalidates a compromised campus's new certificates; provisional unless a suspension confirms it", async function () {
    const { cc, c1, c2, c3, c4, c5 } = await loadFixture(deployConsortium);
    await cc.connect(c5).issue(h("pdf-before"), 1);
    const since = (await now()) + 1n;
    await ethers.provider.send("evm_setNextBlockTimestamp", [Number(since)]);
    await cc.connect(c5).issue(h("pdf-forged"), 1);
    // backdating is bounded and the target cannot vote on its own declaration
    await expect(cc.connect(c1).propose(COMPROMISE, c5.address, 0, hex((await now()) - 8n * BigInt(DAY)))).to.be.revertedWithCustomError(cc, "InvalidData");
    await cc.connect(c1).propose(COMPROMISE, c5.address, 0, hex(since));
    await expect(cc.connect(c5).vote(0)).to.be.revertedWithCustomError(cc, "InvalidTarget");
    await cc.connect(c2).vote(0);
    // c4 stays silent: 3 of the other 4 are enough for the emergency declaration
    await expect(cc.connect(c3).vote(0)).to.emit(cc, "CampusCompromised").withArgs(5n, since, false);
    expect((await cc.verify(h("pdf-before")))[0]).to.equal(true);
    expect((await cc.verify(h("pdf-forged")))[0]).to.equal(false);
    // without a confirming suspension the declaration lapses after 14 days
    await ethers.provider.send("evm_increaseTime", [15 * DAY]);
    await ethers.provider.send("evm_mine", []);
    expect((await cc.verify(h("pdf-forged")))[0]).to.equal(true);
    // a new declaration confirmed by a suspension (four fifths of the others) stays in force
    await cc.connect(c1).propose(COMPROMISE, c5.address, 0, hex(await now()));
    await cc.connect(c2).vote(1);
    await cc.connect(c3).vote(1);
    await cc.connect(c5).issue(h("pdf-forged-2"), 1);
    expect((await cc.verify(h("pdf-forged-2")))[0]).to.equal(false);
    await cc.connect(c1).propose(SUSPEND, c5.address, 0, Z);
    for (const s of [c2, c3]) await cc.connect(s).vote(2);
    await expect(cc.connect(c4).vote(2)).to.emit(cc, "MemberSuspended");
    expect((await cc.compromiseAt(5, 1)).confirmed).to.equal(true);
    await ethers.provider.send("evm_increaseTime", [30 * DAY]);
    await ethers.provider.send("evm_mine", []);
    expect((await cc.verify(h("pdf-forged-2")))[0]).to.equal(false);
    expect((await cc.verify(h("pdf-before")))[0]).to.equal(true);
  });

  it("T15 input validation: malformed deployments, proposals and transfers are rejected", async function () {
    const { cc, c1, c2, c3, c4, c5, outsider, newcomer } = await loadFixture(deployConsortium);
    const F = await ethers.getContractFactory("CertificateConsortium");
    await expect(F.deploy([c1.address], [1, 2], [fp(1)])).to.be.revertedWithCustomError(F, "InvalidTarget");
    await expect(F.deploy([c1.address, c2.address], [1, 1], [fp(1), fp(2)])).to.be.revertedWithCustomError(F, "InvalidCampus");
    await expect(F.deploy([c1.address], [1], [Z])).to.be.revertedWithCustomError(F, "InvalidData");
    await expect(cc.connect(c1).propose(ADMIT, c2.address, 6, fp(6))).to.be.revertedWithCustomError(cc, "InvalidTarget");
    await expect(cc.connect(c1).propose(ADMIT, ethers.ZeroAddress, 6, fp(6))).to.be.revertedWithCustomError(cc, "InvalidTarget");
    await expect(cc.connect(c1).propose(ADMIT, newcomer.address, 2, fp(6))).to.be.revertedWithCustomError(cc, "InvalidCampus");
    await expect(cc.connect(c1).propose(ADMIT, newcomer.address, 0, fp(6))).to.be.revertedWithCustomError(cc, "InvalidCampus");
    await expect(cc.connect(c1).propose(SUSPEND, c1.address, 0, Z)).to.be.revertedWithCustomError(cc, "InvalidTarget");
    await expect(cc.connect(c1).propose(SUSPEND, outsider.address, 0, Z)).to.be.revertedWithCustomError(cc, "InvalidTarget");
    await expect(cc.connect(c1).propose(READMIT, c2.address, 0, Z)).to.be.revertedWithCustomError(cc, "InvalidTarget");
    await expect(cc.connect(c1).propose(ROTATE, outsider.address, 0, fp(9))).to.be.revertedWithCustomError(cc, "InvalidTarget");
    await expect(cc.connect(c1).propose(ROTATE, c1.address, 0, Z)).to.be.revertedWithCustomError(cc, "InvalidData");
    await expect(cc.connect(c1).propose(COMPROMISE, c1.address, 0, hex(await now()))).to.be.revertedWithCustomError(cc, "InvalidTarget");
    await expect(cc.connect(c1).propose(COMPROMISE, outsider.address, 0, hex(await now()))).to.be.revertedWithCustomError(cc, "InvalidTarget");
    await expect(cc.connect(c1).propose(COMPROMISE, c2.address, 0, Z)).to.be.revertedWithCustomError(cc, "InvalidData");
    await expect(cc.connect(c1).propose(COMPROMISE, c2.address, 0, hex((await now()) + 1000n))).to.be.revertedWithCustomError(cc, "InvalidData");
    expect(await cc.signingCertAt(1, 0)).to.equal(Z); // no certificate registered before deployment
    await expect(cc.connect(c1).recordTransfer(99, 2)).to.be.revertedWithCustomError(cc, "UnknownCertificate");
    await cc.connect(c1).issue(h("pdf-t"), 1);
    await expect(cc.connect(c1).recordTransfer(1, 1)).to.be.revertedWithCustomError(cc, "InvalidCampus");
    await expect(cc.connect(c1).recordTransfer(1, 9)).to.be.revertedWithCustomError(cc, "InvalidCampus");
    await expect(cc.connect(c1).revoke(99)).to.be.revertedWithCustomError(cc, "UnknownCertificate");
    await cc.connect(c1).revoke(1);
    await expect(cc.connect(c1).revoke(1)).to.be.revertedWithCustomError(cc, "AlreadyInvalid");
    await expect(cc.connect(c1).recordTransfer(1, 2)).to.be.revertedWithCustomError(cc, "AlreadyInvalid");
    await expect(cc.certificate(42)).to.be.revertedWithCustomError(cc, "ERC721NonexistentToken");
    expect(await cc.supportsInterface("0xb45a3c0e")).to.equal(true); // ERC-5192
    await cc.connect(c1).propose(SUSPEND, c5.address, 0, Z);
    for (const s of [c2, c3, c4]) await cc.connect(s).vote(0);
    await cc.connect(c1).issue(h("pdf-u"), 1);
    await expect(cc.connect(c1).recordTransfer(2, 5)).to.be.revertedWithCustomError(cc, "InvalidCampus"); // suspended campus
  });

  it("T16 recovery: after readmission, the campus's certificate renewal ends its compromise period", async function () {
    const { cc, c1, c2, c3, c4, c5 } = await loadFixture(deployConsortium);
    const since = await now();
    await cc.connect(c1).propose(SUSPEND, c5.address, 0, hex(since));
    for (const s of [c2, c3, c4]) await cc.connect(s).vote(0);
    expect(await cc.compromiseCount(5)).to.equal(1n);
    await cc.connect(c1).propose(READMIT, c5.address, 0, Z);
    for (const s of [c2, c3]) await cc.connect(s).vote(1);
    await cc.connect(c5).issue(h("pdf-still-compromised"), 1);
    expect((await cc.verify(h("pdf-still-compromised")))[0]).to.equal(false);
    await cc.connect(c5).propose(ROTATE, c5.address, 0, fp(505));
    for (const s of [c1, c2]) await cc.connect(s).vote(2);
    expect((await cc.compromiseAt(5, 0)).until).to.not.equal(0n);
    await cc.connect(c5).issue(h("pdf-new-key"), 1);
    expect((await cc.verify(h("pdf-new-key")))[0]).to.equal(true);
    expect((await cc.verify(h("pdf-still-compromised")))[0]).to.equal(false);
  });
  it("T17 found by the model-based tests: stale proposals cannot execute and no declaration reaches back more than 7 days", async function () {
    const { cc, c1, c2, c3, c4, c5 } = await loadFixture(deployConsortium);
    // two suspension proposals against the same campus: once one executes, the other can no longer collect votes,
    // so activeMembers cannot be decremented twice
    await cc.connect(c1).propose(SUSPEND, c5.address, 0, Z);
    await cc.connect(c2).propose(SUSPEND, c5.address, 0, Z);
    for (const s of [c2, c3, c4]) await cc.connect(s).vote(0);
    expect(await cc.activeMembers()).to.equal(4n);
    await expect(cc.connect(c1).vote(1)).to.be.revertedWithCustomError(cc, "StaleProposal");
    // the same holds for a readmission proposed twice
    await cc.connect(c1).propose(READMIT, c5.address, 0, Z);
    await cc.connect(c2).propose(READMIT, c5.address, 0, Z);
    await cc.connect(c2).vote(2);
    await cc.connect(c3).vote(2);
    expect(await cc.activeMembers()).to.equal(5n);
    await expect(cc.connect(c3).vote(3)).to.be.revertedWithCustomError(cc, "StaleProposal");
    // a suspension that also declares a compromise is held to the same seven-day bound as a declaration
    await expect(cc.connect(c1).propose(SUSPEND, c5.address, 0, hex((await now()) - 30n * BigInt(DAY))))
      .to.be.revertedWithCustomError(cc, "InvalidData");
    await expect(cc.connect(c1).propose(SUSPEND, c5.address, 0, hex((await now()) + 1000n)))
      .to.be.revertedWithCustomError(cc, "InvalidData");
    // a declaration voted late is clamped to seven days before its execution
    const since = await now();
    await cc.connect(c1).propose(COMPROMISE, c4.address, 0, hex(since));
    await cc.connect(c2).vote(4);
    await ethers.provider.send("evm_increaseTime", [10 * DAY]);
    await ethers.provider.send("evm_mine", []);
    await cc.connect(c3).vote(4);
    const c = await cc.compromiseAt(4, 0);
    expect(c.declaredAt - c.since).to.equal(BigInt(7 * DAY));
    expect(c.since).to.be.greaterThan(since);
  });
});
