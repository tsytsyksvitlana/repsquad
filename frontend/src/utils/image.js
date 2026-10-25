import { IMAGE } from "../config.js";

/** Draws an image file onto a canvas and returns a JPEG data URL. `layout(bitmap)` picks the size and the source crop. */
async function renderJpeg(file, layout) {
  const bitmap = await createImageBitmap(file);
  try {
    const { width, height, crop } = layout(bitmap);
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    canvas.getContext("2d").drawImage(bitmap, ...crop, 0, 0, width, height);
    return canvas.toDataURL("image/jpeg", IMAGE.jpegQuality);
  } finally {
    bitmap.close();
  }
}

/** Center-crops an image file to a square and downsizes it. */
export const resizeImage = (file, size = IMAGE.avatarSize) => renderJpeg(file, ({ width, height }) => {
  const side = Math.min(width, height);
  return { width: size, height: size, crop: [(width - side) / 2, (height - side) / 2, side, side] };
});

/** Downsizes an image file to fit into maxSide x maxSide, keeping its aspect ratio. */
export const fitImage = (file, maxSide = IMAGE.postMaxSide) => renderJpeg(file, ({ width, height }) => {
  const scale = Math.min(1, maxSide / Math.max(width, height));
  return { width: Math.round(width * scale), height: Math.round(height * scale), crop: [0, 0, width, height] };
});
