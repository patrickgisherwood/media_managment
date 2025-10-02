from PIL import Image
import imagehash


file1 = r"C:\Users\patri\Desktop\Photo_MetaData_Test\output-copy\2024\20240302_125225-07.jpg"
file2 = r"C:\Users\patri\Desktop\Photo_MetaData_Test\sample_images\IMG_0948.jpg"
#file3 = r"C:\Users\patri\Desktop\Photo_MetaData_Test\output-copy\2024\20240117_144428-01.jpg"


def get_pixel_only_hash(path):
    with Image.open(path) as img:
        # Convert to a fixed format so compression artifacts don’t alter the hash
        img = img.convert("RGB")  # ensure consistent color mode
        img = img.resize((256, 256), Image.LANCZOS)  # fixed size normalization
        return imagehash.phash(img)  # or ahash/dhash


hash1 = get_pixel_only_hash(file1)
hash2 = get_pixel_only_hash(file2)

print(hash1)
print(hash2)