import { describe, expect, it } from "bun:test";
import {
  CryptoSigner,
  type FraudAssessmentPayload,
} from "../src/crypto/signer.js";

describe("CryptoSigner Tests", () => {
  const secretKey = "test-secret-key-12345";
  const signer = new CryptoSigner(secretKey);

  const createPayload = (
    overrides: Partial<FraudAssessmentPayload> = {},
  ): FraudAssessmentPayload => ({
    customer_id: "user_100",
    amount: 49.99,
    risk_score: 0.02,
    status: "LOW_RISK",
    evaluated_at: "2026-08-17T20:00:00.000Z",
    ...overrides,
  });

  it("should generate a valid HMAC-SHA256 signature for a payload", () => {
    const payload = createPayload();
    const signature = signer.sign(payload);

    expect(signature).toBeString();
    expect(signature.startsWith("sha256:")).toBe(true);
    expect(signature.length).toBe(71);
  });

  it("should verify a valid signature successfully", () => {
    const payload = createPayload();
    const signature = signer.sign(payload);

    expect(signer.verify(payload, signature)).toBe(true);
  });

  it("should detect tampered risk_score", () => {
    const payload = createPayload();
    const signature = signer.sign(payload);
    const tamperedPayload = createPayload({ risk_score: 0.99 });

    expect(signer.verify(tamperedPayload, signature)).toBe(false);
  });

  it("should detect tampered customer_id or amount", () => {
    const payload = createPayload();
    const signature = signer.sign(payload);

    expect(
      signer.verify(createPayload({ customer_id: "user_999" }), signature),
    ).toBe(false);
    expect(signer.verify(createPayload({ amount: 5000.0 }), signature)).toBe(
      false,
    );
  });

  it("should fail verification with wrong secret key", () => {
    const payload = createPayload();
    const signature = signer.sign(payload);
    const attackerSigner = new CryptoSigner("different-secret-key");

    expect(attackerSigner.verify(payload, signature)).toBe(false);
  });
});
