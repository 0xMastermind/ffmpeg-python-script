import os
import argparse
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, UnidentifiedImageError
from tqdm import tqdm

EXTS = ('.jpg', '.jpeg', '.png', '.tif', '.tiff')

def load_logo(logo_path, opacity):
    """
    Load and process the logo image, adjusting its opacity.
    """
    try:
        logo = Image.open(logo_path).convert("RGBA")
        if opacity < 1:
            alpha = logo.split()[3]
            alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
            logo.putalpha(alpha)
        return logo
    except UnidentifiedImageError:
        raise ValueError(f"Failed to read logo from {logo_path}. Ensure it's a valid image format.")
    except Exception as e:
        raise RuntimeError(f"An error occurred: {e}")

def process_image(image_path, logo, text, position, padding, scale, font_path, font_size, text_opacity):
    """
    Process a single image, adding logo and/or text watermark.
    """
    try:
        image = Image.open(image_path).convert("RGBA")
        image_width, image_height = image.size

        if logo:
            logo = resize_logo(logo, image_width, image_height, scale)
            paste_x, paste_y = get_paste_position(position, image_width, image_height, logo.width, logo.height, padding)
            image.paste(logo, (paste_x, paste_y), logo)

        if text:
            image = add_text_watermark(image, text, position, padding, font_path, font_size, text_opacity)

        return image
    except UnidentifiedImageError:
        print(f"Skipped {image_path}. Unsupported image format.")
        return None
    except Exception as e:
        print(f"An error occurred while processing {image_path}: {e}")
        return None

def resize_logo(logo, image_width, image_height, scale):
    """
    Resize the logo based on the scale percentage of the image's shorter side.
    """
    shorter_side = min(image_width, image_height)
    new_logo_width = int(shorter_side * scale / 100)
    logo_aspect_ratio = logo.width / logo.height
    new_logo_height = int(new_logo_width / logo_aspect_ratio)
    return logo.resize((new_logo_width, new_logo_height), Image.LANCZOS)

def get_paste_position(position, image_width, image_height, element_width, element_height, padding):
    """
    Calculate the position where the watermark should be pasted.
    """
    if position == 'topleft':
        return padding, padding
    elif position == 'topright':
        return image_width - element_width - padding, padding
    elif position == 'bottomleft':
        return padding, image_height - element_height - padding
    elif position == 'bottomright':
        return image_width - element_width - padding, image_height - element_height - padding
    elif position == 'center':
        return (image_width - element_width) // 2, (image_height - element_height) // 2

def add_text_watermark(image, text, position, padding, font_path, font_size, text_opacity):
    """
    Add text watermark to the image.
    """
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_path, font_size)
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
    text_x, text_y = get_paste_position(position, image.width, image.height, text_width, text_height, padding)

    text_layer = Image.new('RGBA', image.size, (255, 255, 255, 0))
    text_draw = ImageDraw.Draw(text_layer)
    text_draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, int(255 * text_opacity)))
    return Image.alpha_composite(image, text_layer)

def save_image(image, save_path, image_format, dpi):
    """
    Save the image to the specified path.
    """
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    if image_format == 'JPEG':
        image.convert('RGB').save(save_path, format=image_format, quality=100, dpi=dpi)
    else:
        image.save(save_path, format=image_format, dpi=dpi)

def add_watermark(directory, logo_path, text, position, new_directory, padding, scale, opacity, font_path, font_size, text_opacity):
    """
    Add watermark to all images in the specified directory.
    """
    logo = load_logo(logo_path, opacity) if logo_path else None
    image_files = []

    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.lower().endswith(EXTS) and (not logo_path or filename.lower() != os.path.basename(logo_path).lower()):
                image_files.append(os.path.join(dirpath, filename))

    for full_path in tqdm(image_files, desc="Processing images"):
        print(f"Processing: {full_path}")
        image = process_image(full_path, logo, text, position, padding, scale, font_path, font_size, text_opacity)
        
        if image:
            relative_path = os.path.relpath(os.path.dirname(full_path), directory)
            save_directory = new_directory if new_directory else directory
            final_save_directory = os.path.join(save_directory, relative_path)
            new_image_path = os.path.join(final_save_directory, os.path.basename(full_path))
            
            image_format = 'PNG' if full_path.lower().endswith(('.png', '.tif', '.tiff')) else 'JPEG'
            dpi = image.info.get('dpi', (72, 72))

            save_image(image, new_image_path, image_format, dpi)
            print(f'Added watermark to {new_image_path}')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A script to add watermarks to images. Given a directory, this will traverse through all its images and apply the specified watermark. The resulting watermarked images can be saved in the same directory or a new specified directory, maintaining the original directory structure.")

    parser.add_argument('dir', help="Directory containing the images you want to watermark. The script will search recursively within this directory.", metavar='SourceDirectory')
    parser.add_argument('logo', help="Path to the logo image that will be used as the watermark.", metavar='WatermarkLogoPath', nargs='?', default=None)
    parser.add_argument('--text', help="Text to be used as a watermark.", metavar='WatermarkText', default=None)
    parser.add_argument('--pos', choices=['topleft', 'topright', 'bottomleft', 'bottomright', 'center'], default='center', help="Specifies the position of the watermark on the image. Default is 'center'.")
    parser.add_argument('--new_dir', default=None, help="An optional directory where the watermarked images will be saved. If not provided, watermarked images will overwrite originals in the source directory. The original directory structure will be maintained.", metavar='DestinationDirectory')
    parser.add_argument('--padding', type=int, default=0, help="Specifies the padding (in pixels) around the watermark, useful when watermark is positioned at the corners. Default is 0, meaning no padding.")
    parser.add_argument('--scale', type=float, default=20, help="Resize the watermark based on a percentage of the image's width. E.g., for 10% of the image's width, provide 10.")
    parser.add_argument('--opacity', type=float, default=1.0, help="Opacity level of the watermark (0.0 to 1.0). Default is 1.0 (fully opaque).")
    parser.add_argument('--font', help="Path to the font file to be used for the text watermark.", default="Morrison-ExtraBold.ttf", metavar='FontPath')
    parser.add_argument('--fontsize', type=int, default=36, help="Font size of the text watermark. Default is 36.", metavar='FontSize')
    parser.add_argument('--text_opacity', type=float, default=1.0, help="Opacity level of the text watermark (0.0 to 1.0). Default is 1.0 (fully opaque).")

    args = parser.parse_args()
    add_watermark(args.dir, args.logo, args.text, args.pos, args.new_dir, args.padding, args.scale, args.opacity, args.font, args.fontsize, args.text_opacity)
