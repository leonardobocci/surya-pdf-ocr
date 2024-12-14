[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

OCR: [Surya](https://github.com/VikParuchuri/surya)\
Packaging: [Uv](https://github.com/astral-sh/uv)\
Dataframes: [Polars](https://github.com/pola-rs/polars)

This was a quick project done for my Mom. Her job involves manually looking at PDF orders and putting order numbers, ordered items and quantities into a custom company system.

I took this as a chance to play around with Surya (a pretrained deep learning model for optical character recognition).
It does an incredible job at parsing the PDFs in question, with human-level accuracy of parsing.

Some further text processing is done to then bring Surya's outputs into the exact format required by the system.