// Sanity checks for the comparison designs D1 and D3 (not part of the twelve tests in Table V).
const { expect } = require("chai");
const { ethers } = require("hardhat");

const h = (s) => ethers.keccak256(ethers.toUtf8Bytes(s));

describe("Baselines (D1, D3) · sanity", function () {
  it("D1 prototype contract (verbatim): issue, query, validate, revoke; admin only", async function () {
    const [, other] = await ethers.getSigners();
    const d1 = await ethers.deployContract("CertificadosContract");
    await d1.emitirCertificado(123, "Esteban", "Trejo", "Barriga", "236022004", "Matemáticas", "25/7/25");
    expect(await d1.validarCertificado(123)).to.equal(true);
    expect((await d1.obtenerCertificado(123))[3]).to.equal("236022004");
    await expect(d1.connect(other).revocarCertificado(123)).to.be.revertedWith(
      "Solo el administrador puede ejecutar esta funcion",
    );
    await d1.revocarCertificado(123);
    expect(await d1.validarCertificado(123)).to.equal(false);
    // The prototype overwrites an existing id without any check (no duplicate protection).
    await d1.emitirCertificado(123, "Otro", "Nombre", "Distinto", "1", "x", "1/1/26");
    expect((await d1.obtenerCertificado(123))[0]).to.equal("Otro");
  });

  it("D3 registry: same rules as D2 without tokens", async function () {
    const s = await ethers.getSigners();
    const d3 = await ethers.deployContract("HashRegistry", [s.slice(0, 5).map((x) => x.address), [1, 2, 3, 4, 5], [1, 2, 3, 4, 5].map((i) => ethers.keccak256(ethers.toUtf8Bytes(`x509-campus-${i}`)))]);
    await d3.connect(s[0]).issue(h("a"), 1);
    await expect(d3.connect(s[1]).issue(h("a"), 1)).to.be.revertedWithCustomError(d3, "HashAlreadyRegistered");
    await expect(d3.connect(s[1]).recordTransfer(1, 3)).to.be.revertedWithCustomError(d3, "NotCurrentCampus");
    await d3.connect(s[0]).recordTransfer(1, 2);
    await expect(d3.connect(s[1]).revoke(1)).to.be.revertedWithCustomError(d3, "NotIssuer");
    await d3.connect(s[0]).revoke(1);
    expect((await d3.verify(h("a")))[0]).to.equal(false);
  });
});
