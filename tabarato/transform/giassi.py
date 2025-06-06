from .transformer import Transformer
from tabarato.loader import Loader
import pandas as pd
import re


class GiassiTransformer(Transformer):
    @classmethod
    def slug(cls) -> str:
        return "giassi"

    @classmethod
    def id(cls) -> int:
        return 3

    @classmethod
    def transform(cls) -> pd.DataFrame:
        df = Loader.read("bronze", cls.slug())

        df.rename(columns={
            "productName": "name",
            "productId": "ref_id",
            "multiplicador": "weight",
            "unidade": "measure"},
            inplace=True)
        
        df[["image_url", "cart_link", "price", "old_price"]] = df.apply(cls._extract_item_info, axis=1)

        df["name"] = df.apply(cls._remove_word, axis=1)

        return super().transform(df)

    @classmethod
    def _extract_item_info(cls, row):
        items = row["items"]
        
        if not items.any():
            return pd.Series({"cart_link": None, "price": None, "old_price": None})

        values = pd.Series({"image_url": None, "cart_link": None, "price": None, "old_price": None})

        item = items[0]
        if "sellers" in item and item["sellers"].any():
            seller = item["sellers"][0]
            commertial_offer = seller.get("commertialOffer", {})

            values["cart_link"] = seller.get("addToCartLink", None)
            values["price"] = commertial_offer.get("Price", None)
            values["old_price"] = commertial_offer.get("ListPrice", None)
        
        if "images" in item and item["images"].any():
            image = item["images"][0]
            values["image_url"] = image.get("imageUrl", None)
        
        return values

    @classmethod
    def _remove_word(cls, row):
        name = row["name"]
        brand = row["brand"]
        word_to_ignore = "original"
        
        if brand.strip().lower() != word_to_ignore:
            return re.sub(r'\b' + word_to_ignore + r'\b', '', name, flags=re.IGNORECASE).strip()
        return name
