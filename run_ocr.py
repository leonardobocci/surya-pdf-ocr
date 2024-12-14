import os
import glob
import polars as pl
from whenever import LocalDateTime
from pdf2image import convert_from_path
from surya.ocr import run_ocr
from surya.model.detection.model import (
    load_model as load_det_model,
    load_processor as load_det_processor,
)
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor

LOCAL = True  # this is used in Colab if set to false

# set up Surya
langs = ["it"]
det_processor, det_model = load_det_processor(), load_det_model()
rec_model, rec_processor = load_rec_model(), load_rec_processor()


def get_filepaths() -> list:
    """Get all filepaths in the order_docs local directory."""
    if LOCAL:
        files = os.listdir("order_docs")
    else:
        files = glob.glob("./*.pdf")
    return files


def format_filename(filename: str) -> tuple[int, LocalDateTime, str]:
    """Check if filename is already compliant with naming expectation. If not, rename it."""
    if len(filename.split("_")) == 2 and len(filename.split("_")[1]) == 14:
        # date.pdf is 14 digits and there are two parts to the filename - all good
        if LOCAL:
            ordernum = int(filename.split("_")[0])
        else:
            ordernum = int(filename.split("_")[0].replace("./", ""))
        orderdate = LocalDateTime.strptime(
            filename.split("_")[1].split(".")[0], "%Y-%m-%d"
        ).date()
    else:
        ordernum = int(filename.split(" ")[1].split("-")[-1])
        orderdate = LocalDateTime.strptime(
            filename.split(" ")[-1].split(".")[0], "%d-%m-%Y"
        ).date()
        new_filename = f"{ordernum}_{orderdate}.pdf"
        if LOCAL:
            os.rename(
                os.path.join("order_docs", filename),
                os.path.join("order_docs", new_filename),
            )
        else:
            os.rename(
                filename,
                new_filename,
            )
        filename = new_filename
    return ordernum, orderdate, filename


def convert_pdf_to_images(filename: str) -> list:
    """Convert each page of a pdf file into PIL image."""
    if LOCAL:
        return convert_from_path(f"order_docs/{filename}")
    else:
        return convert_from_path(filename)


def ocr_all_pages(images: list) -> list[dict]:
    """Run OCR on all images (pdf pages) of an order."""
    all_pages = []
    pagenum = 0
    for image in images:
        page_ocr = run_ocr(
            [image], [langs], det_model, det_processor, rec_model, rec_processor
        )[0].text_lines
        for line in page_ocr:
            line_dict = line.model_dump()
            line_dict.update({"page": pagenum})
            all_pages.append(line_dict)
        pagenum += 1
    return all_pages


def extract_order_rif(order_ocr: list) -> int:
    """Extract order detail: riferimento, based on last page entry in pdf."""
    for line in order_ocr:
        if "rif" in str.lower(line["text"]):
            char_list_with_rif = line["text"].split(".")
            char_list_with_rif = [s.strip() for s in char_list_with_rif]
            for char in char_list_with_rif:
                try:
                    rif = int(char)
                    return rif
                except ValueError:
                    continue


def extract_ordered_items(order_ocr: list) -> list[dict]:
    """Extract order codes."""
    order_details = []
    for line in order_ocr:
        split_text = line["text"].replace(" ", ".").split(".")
        item_code_chars = [
            entry for entry in split_text if any(chr.isdigit() for chr in entry)
        ][0:3]
        item_code = str.strip("".join(item_code_chars))
        exclude_patterns = ["/", ",", "-", "MM"]
        if len(item_code) == 9 and not any(x in item_code for x in exclude_patterns):
            order_details.append(
                {
                    "item_code": str.strip(item_code),
                    "coordinates": line["bbox"],
                    "page": line["page"],
                }
            )

    for order in order_details:
        y_top_left = order["coordinates"][1]
        y_bottom_right = order["coordinates"][-1]
        center_y_line = (
            y_top_left + y_bottom_right
        ) / 2  # center line of order line item, scroll right to get quantity
        matched_text = []
        for line in order_ocr:
            if (
                line["bbox"][1] < center_y_line < line["bbox"][-1]
                and line["page"] == order["page"]
            ):
                matched_text.append((line["text"]))
        ordered_qty = int(
            [
                str.strip(char)
                for char in matched_text
                if "," in char and len(str.strip(char)) == 5
            ][0][0]
        )
        order["ordered_qty"] = ordered_qty

    return order_details


def format_output(orders: list) -> None:
    order_output = []
    for order in orders:
        for order_detail in order["details"]:
            order_output.append(
                {
                    "Article No.": order_detail["item_code"],
                    "Quantity": order_detail["ordered_qty"],
                    "rif": f'{order["order_number"]}/{order["order_rif"]}',
                }
            )
    pl.DataFrame(order_output).write_excel("FRONT.xlsx")
    if not LOCAL:
        files.download("FRONT.xlsx")  # noqa:F821


# file preprocessing
filenames = get_filepaths()
orders = []
for filename in filenames:
    ordernum, orderdate, newfilename = format_filename(filename)
    orders.append(
        {
            "order_number": ordernum,
            "order_date": orderdate,
            "images": convert_pdf_to_images(newfilename),
        }
    )

# orders dict is now ready for OCR
for order in orders:
    order_ocr = ocr_all_pages(order["images"])
    order["order_rif"] = extract_order_rif(order_ocr)
    order["details"] = extract_ordered_items(order_ocr)

# now format output and download file
format_output(orders)