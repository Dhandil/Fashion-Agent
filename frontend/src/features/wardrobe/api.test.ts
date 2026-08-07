import { describe, expect, it } from "vitest";
import {
  validateWardrobeImageFile,
  WARDROBE_IMAGE_MAX_BYTES,
} from "@/features/wardrobe/api";

function makeFile(name: string, type: string, size: number): File {
  return new File([new Uint8Array(size)], name, { type });
}

describe("衣物图片客户端校验", () => {
  it("接受 JPEG 和 PNG", () => {
    expect(validateWardrobeImageFile(makeFile("a.jpg", "image/jpeg", 1024))).toBeNull();
    expect(validateWardrobeImageFile(makeFile("a.png", "image/png", 1024))).toBeNull();
  });

  it("拒绝 WebP 等非支持格式（与 GLM-4V-Flash 能力一致）", () => {
    const err = validateWardrobeImageFile(makeFile("a.webp", "image/webp", 1024));
    expect(err).toMatch(/JPEG 或 PNG/);
    expect(validateWardrobeImageFile(makeFile("a.gif", "image/gif", 1024))).toMatch(/JPEG 或 PNG/);
  });

  it("拒绝超过 5MB 的图片", () => {
    const err = validateWardrobeImageFile(
      makeFile("big.jpg", "image/jpeg", WARDROBE_IMAGE_MAX_BYTES + 1),
    );
    expect(err).toMatch(/5MB/);
  });

  it("5MB 边界内通过", () => {
    expect(
      validateWardrobeImageFile(makeFile("ok.jpg", "image/jpeg", WARDROBE_IMAGE_MAX_BYTES)),
    ).toBeNull();
  });
});
