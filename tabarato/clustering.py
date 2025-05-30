from .utils.string_utils import get_words
from .loader import Loader
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import nltk
from nltk.corpus import stopwords
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score, davies_bouldin_score
from sklearn.manifold import TSNE
import dotenv
import seaborn as sns
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel
import torch


dotenv.load_dotenv()

nltk.download("stopwords", quiet=True)

class Clustering:
    PORTUGUESE_STOPWORDS = set(stopwords.words("portuguese"))
    STORE = ""

    @classmethod
    def process(cls, store, method) -> pd.DataFrame:
        cls.STORE = store
        df = Loader.read("silver", store)
        df = df[~((df["price"] == 0) & (df["old_price"] == 0))]

        embedded_names = cls._get_embeddings(df["name"].tolist(), method)
        df["embedded_name"] = embedded_names.tolist()
        db = DBSCAN(
            eps=0.01,
            min_samples=1,
            metric="cosine"
        ).fit(embedded_names)

        df["cluster"] = db.labels_

        cls._evaluate_clusters(embedded_names, df["cluster"].values)

        df_grouped = df.groupby(["brand", "cluster"]).agg({
            "name": list,
            "embedded_name": list,
            "store_id": list,
            "weight": list,
            "measure": list,
            "price": list,
            "old_price": list,
            "link": list,
            "cart_link": list,
            "image_url": list,
            "ref_id": list
        }).reset_index()

        df_grouped["variations"] = df_grouped.apply(cls._group_variations, axis=1)
        df_grouped["name"] = df_grouped["name"].apply(lambda row: row[0])
        df_grouped["embedded_name"] = df_grouped["embedded_name"].apply(lambda row: row[0])
        df_grouped.drop(columns=["weight", "measure", "store_id", "price", "old_price", "link", "cart_link", "image_url", "ref_id"], inplace=True)

        return df_grouped

    @classmethod
    def load(cls, df):
        # df = ti.xcom_pull(task_ids = "process_task")
        Loader.load(df, layer="gold", name=cls.STORE)

    @classmethod
    def _get_embeddings(cls, names, method):
        device = "cuda" if torch.cuda.is_available() else "cpu"

        names = [
            " ".join([word for word in get_words(name.lower()) if word not in cls.PORTUGUESE_STOPWORDS])
            for name in names
        ]
        
        if method == 0:
            print("Cluster with BERT")
            tokenizer = AutoTokenizer.from_pretrained("neuralmind/bert-base-portuguese-cased")
            model = AutoModel.from_pretrained("neuralmind/bert-base-portuguese-cased").to(device)
            model.eval()

            batch_size = 128
            embedded_names = []

            for i in range(0, len(names), batch_size):
                batch = names[i:i+batch_size]

                inputs = tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=64,
                    return_tensors="pt"
                ).to(device)

                with torch.no_grad():
                    outputs = model(**inputs)

                batch_embeddings = outputs.last_hidden_state.mean(dim=1).cpu().numpy()
                embedded_names.append(batch_embeddings)
        elif method == 1:
            print("Cluster with Sentence-BERT")
            sentence_model = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2", device=device)
            embedded_names = sentence_model.encode(names, normalize_embeddings=True)

        return np.vstack(embedded_names)

    @classmethod
    def _evaluate_clusters(cls, features, cluster_labels):
        valid_mask = cluster_labels != -1
        n_clusters = len(np.unique(cluster_labels[valid_mask]))
        
        print("\n=== Clustering Evaluation ===")
        print(f"Number of clusters: {n_clusters}")
        print(f"Noise points: {np.sum(cluster_labels == -1)}")
        
        if n_clusters > 1:
            print(f"\nMetrics on clean data ({np.sum(valid_mask)} points):")
            print(f"Silhouette Score: {silhouette_score(features[valid_mask], cluster_labels[valid_mask]):.3f}")
            print(f"Davies-Bouldin Index: {davies_bouldin_score(features[valid_mask], cluster_labels[valid_mask]):.3f}")

        # tsne = TSNE(n_components=2, random_state=42)
        # reduced = tsne.fit_transform(features)
        # plt.figure(figsize=(14,6))
        # plt.subplot(1,2,1)
        # sns.scatterplot(
        #     x=reduced[:,0], 
        #     y=reduced[:,1], 
        #     hue=cluster_labels,
        #     palette='tab20',
        #     legend=False
        # )
        # plt.subplot(1,2,2)
        # sns.kdeplot(
        #     x=reduced[:,0], 
        #     y=reduced[:,1], 
        #     cmap='viridis', 
        #     fill=True
        # )
        # plt.show()

    @classmethod
    def _group_variations(cls, row: pd.Series) -> dict:
        variations = [
            {
                "name": n, "embedded_name": en, "weight": w, "measure": m, "store_id": s, "price": p,
                "old_price": op, "link": l, "cart_link": cl, "image_url": img, "ref_id": ri
            }
            for n, en, w, m, s, p, op, l, cl, img, ri in zip(
                row["name"], row["embedded_name"], row["weight"], row["measure"], row["store_id"],
                row["price"], row["old_price"], row["link"], row["cart_link"], row["image_url"], row["ref_id"]
            )
        ]

        df = pd.DataFrame(variations)

        df_grouped = df.groupby(["weight", "measure"], as_index=False).agg(
            name=("name", "first"), # Apenas um nome representativo por variação
            # embedded_name=("embedded_name", "first"), # Apenas um nome representativo por variação
            image_url=("image_url", "first"), # Apenas uma imagem representativa por variação
            sellers=("store_id", lambda x: [
                {
                    "store_id": store,
                    "price": price,
                    "old_price": old_price,
                    "link": link,
                    "cart_link": cart_link,
                    "ref_id": ref_id
                }
                for store, price, old_price, link, cart_link, ref_id in zip(
                    x, df.loc[x.index, "price"], df.loc[x.index, "old_price"],
                    df.loc[x.index, "link"], df.loc[x.index, "cart_link"], df.loc[x.index, "ref_id"]
                )
            ])
        )

        return df_grouped.to_dict(orient="records")
