// Property-based (model-based) tests of the governance state machine. Run: npx hardhat test
//
// A seeded pseudo-random generator drives long sequences of proposals, votes, issuances, revocations and clock
// advances by members, suspended members and outsiders, including invalid ones. After every step the contract is
// compared with a reference model written from the rules in the paper (Section 3.4), and these properties are
// checked:
//   P1 every call succeeds or reverts exactly as the model predicts;
//   P2 activeMembers equals the number of active members, and member/campus records match the model;
//   P3 a proposal executes exactly when its threshold is met, with the target never voting on a proposal against it;
//   P4 a stale proposal (its target no longer in the required state) can never execute;
//   P5 the signing-certificate history is append-only and signingCertAt(i, t) matches the model at sampled times;
//   P6 every compromise period starts at most MAX_BACKDATE before, and not after, its declaration;
//   P7 verify(h) matches the model: valid unless revoked or issued inside a confirmed or not-yet-lapsed period.
// PBT_SEED and PBT_RUNS (sequences of PBT_STEPS steps) make a failure reproducible: the failing seed is printed.
const { expect } = require("chai");
const { ethers, network } = require("hardhat");
const { loadFixture } = require("@nomicfoundation/hardhat-toolbox/network-helpers");

const RUNS = Number(process.env.PBT_RUNS || 50);
const STEPS = Number(process.env.PBT_STEPS || 60);
const SEED = Number(process.env.PBT_SEED || 20271027);
const K = { Admit: 0, Suspend: 1, Readmit: 2, RotateCert: 3, DeclareCompromise: 4 };
const DAY = 24 * 3600;
const MAX_BACKDATE = 7 * DAY;
const PROVISIONAL = 14 * DAY;
const fpOf = (s) => ethers.keccak256(ethers.toUtf8Bytes(s));

function prng(seed) { // mulberry32
  let a = seed >>> 0;
  const next = () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  return { next, int: (n) => Math.floor(next() * n), pick: (xs) => xs[Math.floor(next() * xs.length)] };
}

async function deploy() {
  const signers = await ethers.getSigners();
  const founders = signers.slice(0, 5);
  const cc = await ethers.deployContract("CertificateConsortium", [
    founders.map((s) => s.address), [1, 2, 3, 4, 5], [1, 2, 3, 4, 5].map((i) => fpOf(`cert-${i}-0`)),
  ]);
  const t0 = Number((await ethers.provider.getBlock("latest")).timestamp);
  return { cc, signers: signers.slice(0, 8), t0 };
}

// ------------------------------------------------------------------ reference model (paper, Section 3.4)
class Model {
  constructor(signers, t0) {
    this.now = t0;
    this.members = new Map(); // address -> {exists, active, campus}
    this.campusAccount = new Map();
    this.certs = new Map(); // campus -> [{fp, from}]
    this.compromises = new Map(); // campus -> [{since, until, declaredAt, confirmed}]
    this.proposals = [];
    this.issued = new Map(); // hash -> {campus, at, valid}
    signers.slice(0, 5).forEach((s, i) => this._admit(s.address, i + 1, fpOf(`cert-${i + 1}-0`), t0));
  }
  m(a) { return this.members.get(a) || { exists: false, active: false, campus: 0 }; }
  get active() { return [...this.members.values()].filter((x) => x.active).length; }
  _admit(a, campus, fp, t) {
    this.members.set(a, { exists: true, active: true, campus });
    this.campusAccount.set(campus, a);
    this.certs.set(campus, [{ fp, from: t }]);
    this.compromises.set(campus, []);
  }
  // precondition of a proposal kind on the current state (checked when proposing and again when voting)
  applicable(kind, target, campus, data, proposer) {
    const t = this.m(target);
    switch (kind) {
      case K.Admit: return !t.exists && target !== ethers.ZeroAddress && campus !== 0 && !this.campusAccount.has(campus) && data !== ethers.ZeroHash;
      case K.Suspend: return t.active && target !== proposer;
      case K.Readmit: return t.exists && !t.active;
      case K.RotateCert: return target === proposer && t.active && data !== ethers.ZeroHash;
      default: return t.exists && target !== proposer;
    }
  }
  sinceOk(kind, since, t) {
    if (kind === K.Suspend && since === 0) return true; // suspension without a declaration
    return since !== 0 && since <= t && since + MAX_BACKDATE >= t;
  }
  passed(p) {
    const yes = p.voters.size;
    const n = this.active;
    if (p.kind === K.Admit) return yes * 5 >= n * 4;
    if (p.kind === K.Suspend) return yes * 5 >= (n - 1) * 4;
    if (p.kind === K.DeclareCompromise) return yes * 2 > (this.m(p.target).active ? n - 1 : n);
    return yes * 2 > n;
  }
  // returns null if the call must revert, or a function applying the effects
  propose(sender, kind, target, campus, data, t) {
    if (!this.m(sender).active) return null;
    if (!this.applicable(kind, target, campus, data, sender)) return null;
    if ((kind === K.Suspend || kind === K.DeclareCompromise) && !this.sinceOk(kind, Number(BigInt(data)), t)) return null;
    return () => {
      const p = { kind, target, campus, data, voters: new Set(), executed: false, proposer: sender };
      this.proposals.push(p);
      this._vote(p, sender, t);
    };
  }
  vote(sender, id, t) {
    const p = this.proposals[id];
    if (!p || !this.m(sender).active || p.executed || p.voters.has(sender)) return null;
    if ((p.kind === K.Suspend || p.kind === K.DeclareCompromise) && p.target === sender) return null;
    if (!this.applicable(p.kind, p.target, p.campus, p.data, p.proposer)) return null; // stale (P4)
    return () => this._vote(p, sender, t);
  }
  _vote(p, sender, t) {
    p.voters.add(sender);
    if (!this.passed(p)) return;
    p.executed = true;
    const tm = this.m(p.target);
    const since = Math.max(Number(BigInt(p.data)), t - MAX_BACKDATE); // late execution never backdates further
    if (p.kind === K.Admit) this._admit(p.target, p.campus, p.data, t);
    else if (p.kind === K.Suspend) {
      tm.active = false;
      for (const c of this.compromises.get(tm.campus)) if (!c.confirmed && c.until === 0) c.confirmed = true;
      if (BigInt(p.data) !== 0n) this.compromises.get(tm.campus).push({ since, until: 0, declaredAt: t, confirmed: true });
    } else if (p.kind === K.Readmit) tm.active = true;
    else if (p.kind === K.RotateCert) {
      for (const c of this.compromises.get(tm.campus)) if (c.until === 0) c.until = t;
      this.certs.get(tm.campus).push({ fp: p.data, from: t });
    } else this.compromises.get(tm.campus).push({ since, until: 0, declaredAt: t, confirmed: false });
  }
  issue(sender, h, t) {
    if (!this.m(sender).active || this.issued.has(h)) return null;
    return () => this.issued.set(h, { campus: this.m(sender).campus, at: t, valid: true });
  }
  revoke(sender, h) {
    const c = this.issued.get(h);
    if (!c || !this.m(sender).active || c.campus !== this.m(sender).campus || !c.valid) return null;
    return () => { c.valid = false; };
  }
  certAt(campus, t) {
    const hist = this.certs.get(campus) || [];
    for (let i = hist.length - 1; i >= 0; i--) if (hist[i].from <= t) return hist[i].fp;
    return ethers.ZeroHash;
  }
  verifyValid(h, now) {
    const c = this.issued.get(h);
    if (!c.valid) return false;
    return !(this.compromises.get(c.campus) || []).some((p) => c.at >= p.since && (p.until === 0 || c.at < p.until)
      && (p.confirmed || now < p.declaredAt + PROVISIONAL));
  }
}

// ------------------------------------------------------------------ driver
async function send(fn, t) {
  await network.provider.send("evm_setNextBlockTimestamp", [t]);
  try {
    await (await fn()).wait();
    return true;
  } catch (e) {
    if (!/revert/i.test(String(e.message))) throw e;
    return false;
  }
}

async function checkInvariants(cc, model, signers, rnd, ctx) {
  // P2 members and active count
  expect(Number(await cc.activeMembers()), `${ctx} activeMembers`).to.equal(model.active);
  for (const s of signers) {
    const [exists, active, campus] = await cc.members(s.address);
    const m = model.m(s.address);
    expect([exists, active, Number(campus)], `${ctx} member ${s.address}`).to.deep.equal([m.exists, m.active, m.campus]);
  }
  // P3/P4 proposals
  expect(Number(await cc.proposalCount()), `${ctx} proposalCount`).to.equal(model.proposals.length);
  for (let i = 0; i < model.proposals.length; i++) {
    const p = await cc.proposals(i);
    expect([Number(p.yesVotes), p.executed], `${ctx} proposal ${i}`).to.deep.equal([model.proposals[i].voters.size, model.proposals[i].executed]);
    if (model.proposals[i].executed) expect(model.proposals[i].voters.has(model.proposals[i].target) && model.proposals[i].kind !== K.Admit
      && model.proposals[i].kind !== K.Readmit && model.proposals[i].kind !== K.RotateCert).to.equal(false);
  }
  // P5 certificate history and P6 compromise periods
  for (const [campus, hist] of model.certs) {
    for (let k = 0; k < hist.length; k++) {
      expect(await cc.signingCertAt(campus, hist[k].from), `${ctx} cert ${campus}/${k}`).to.equal(hist[k].fp);
    }
    const probe = model.now - rnd.int(30 * DAY);
    expect(await cc.signingCertAt(campus, probe), `${ctx} cert ${campus}@${probe}`).to.equal(model.certAt(campus, probe));
    const list = model.compromises.get(campus);
    expect(Number(await cc.compromiseCount(campus)), `${ctx} compromises ${campus}`).to.equal(list.length);
    for (let k = 0; k < list.length; k++) {
      const c = await cc.compromiseAt(campus, k);
      expect([Number(c.since), Number(c.until), Number(c.declaredAt), c.confirmed], `${ctx} compromise ${campus}/${k}`)
        .to.deep.equal([list[k].since, list[k].until, list[k].declaredAt, list[k].confirmed]);
      expect(c.since <= c.declaredAt && Number(c.since) + MAX_BACKDATE >= Number(c.declaredAt), `${ctx} P6`).to.equal(true);
    }
  }
  // P7 verification
  const now = Number((await ethers.provider.getBlock("latest")).timestamp);
  for (const h of model.issued.keys()) {
    const a = model.verifyValid(h, now), b = model.verifyValid(h, now + 1);
    if (a !== b) continue; // exactly at a lapse boundary: the call's timestamp decides
    const [valid] = await cc.verify(h);
    expect(valid, `${ctx} verify ${h}`).to.equal(a);
  }
}

describe(`Governance state machine · model-based property tests (${RUNS} sequences × ${STEPS} steps, seed ${SEED})`, function () {
  this.timeout(0);
  const stats = { calls: 0, reverts: 0, executed: [0, 0, 0, 0, 0], stale: 0 };

  for (let run = 0; run < RUNS; run++) {
    const seed = SEED + run;
    it(`P1–P7 hold for sequence ${run + 1} (seed ${seed})`, async function () {
      const { cc, signers, t0 } = await loadFixture(deploy);
      const rnd = prng(seed);
      const model = new Model(signers, t0);
      const addrs = signers.map((s) => s.address);
      let nonce = 0;
      for (let step = 0; step < STEPS; step++) {
        const ctx = `seed ${seed} step ${step}`;
        const activeSigners = signers.filter((x) => model.m(x.address).active);
        const sender = rnd.next() < 0.8 && activeSigners.length ? rnd.pick(activeSigners) : rnd.pick(signers);
        const t = model.now + 1;
        const r = rnd.next();
        let predicted, call, what;
        if (r < 0.35) { // propose
          const kind = rnd.int(5);
          // mostly a target that fits the kind, sometimes any address (invalid proposals must revert)
          const fits = addrs.filter((a) => model.applicable(kind, a, 6, fpOf("x"), sender.address)
            || (kind === K.Admit && !model.m(a).exists));
          const target = kind === K.RotateCert && rnd.next() < 0.7 ? sender.address
            : rnd.next() < 0.7 && fits.length ? rnd.pick(fits) : rnd.pick(addrs);
          const free = [6, 7, 8].filter((c) => !model.campusAccount.has(c));
          const campus = rnd.next() < 0.8 && free.length ? rnd.pick(free) : rnd.pick([0, 1, 6, 7, 8]);
          let data;
          if (kind === K.Suspend || kind === K.DeclareCompromise) {
            const off = rnd.next() < 0.7 ? rnd.pick([0, 1, DAY, 6 * DAY, MAX_BACKDATE]) : rnd.pick([MAX_BACKDATE + 1, 30 * DAY, -DAY]);
            data = kind === K.Suspend && rnd.next() < 0.5 ? 0 : t - off;
            data = ethers.toBeHex(Math.max(data, 0), 32);
          } else data = rnd.next() < 0.1 ? ethers.ZeroHash : fpOf(`cert-${seed}-${nonce++}`);
          predicted = model.propose(sender.address, kind, target, campus, data, t);
          call = () => cc.connect(sender).propose(kind, target, campus, data);
          what = `propose kind ${kind} target ${addrs.indexOf(target)} campus ${campus} since-offset ${t - Number(BigInt(data))} by ${addrs.indexOf(sender.address)}`;
        } else if (r < 0.75 && model.proposals.length) { // vote, mostly on recent proposals
          const open = model.proposals.map((q, i) => i).filter((i) => !model.proposals[i].executed);
          const id = rnd.next() < 0.85 && open.length ? rnd.pick(open.slice(-6)) : rnd.int(model.proposals.length + 1);
          const p = model.proposals[id];
          if (p && !p.executed && !model.applicable(p.kind, p.target, p.campus, p.data, p.proposer)) stats.stale++;
          predicted = model.vote(sender.address, id, t);
          call = () => cc.connect(sender).vote(id);
          what = p ? `vote ${id} (kind ${p.kind}, target ${addrs.indexOf(p.target)}, applicable ${model.applicable(p.kind, p.target, p.campus, p.data, p.proposer)}) by ${addrs.indexOf(sender.address)}` : `vote ${id}`;
        } else if (r < 0.87) { // issue
          const h = rnd.next() < 0.1 && model.issued.size ? rnd.pick([...model.issued.keys()]) : fpOf(`pdf-${seed}-${nonce++}`);
          predicted = model.issue(sender.address, h, t);
          call = () => cc.connect(sender).issue(h, 1);
          what = `issue by ${addrs.indexOf(sender.address)}`;
        } else if (r < 0.92 && model.issued.size) { // revoke
          const h = rnd.pick([...model.issued.keys()]);
          predicted = model.revoke(sender.address, h);
          const id = await cc.idByHash(h);
          call = () => cc.connect(sender).revoke(id);
          what = `revoke by ${addrs.indexOf(sender.address)}`;
        } else { // clock advance
          const dt = rnd.pick([60, DAY, 3 * DAY, 8 * DAY, 15 * DAY]);
          model.now += dt;
          await network.provider.send("evm_setNextBlockTimestamp", [model.now]);
          await network.provider.send("evm_mine", []);
          continue;
        }
        const ok = await send(call, t);
        model.now = t;
        stats.calls++;
        expect(ok, `${ctx}: ${what}: ${ok ? "succeeded" : "reverted"} but the model predicted ${predicted ? "success" : "a revert"}`)
          .to.equal(Boolean(predicted));
        if (!ok) {
          stats.reverts++;
          continue;
        }
        const before = model.proposals.map((p) => p.executed);
        predicted();
        model.proposals.forEach((p, i) => { if (p.executed && !before[i]) stats.executed[p.kind]++; });
        await checkInvariants(cc, model, signers, rnd, ctx);
      }
    });
  }

  after(function () {
    console.log(`      model-based tests: ${stats.calls} calls, ${stats.reverts} predicted reverts, executed proposals by kind `
      + `[admit, suspend, readmit, rotate, declare] = [${stats.executed.join(", ")}], ${stats.stale} votes on stale proposals`);
  });
});
