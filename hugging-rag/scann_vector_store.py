import os
import pandas as pd
import numpy as np
import scann

class ScannVectorStore():
    def __init__(self, vector_data, ranker, similarity_algorithm="dot_product", k=100_000):
        self.corpus_container = vector_data.get_df_doc_feature()[["doc_id"]]
        self.corpus_container["scores"] = -1.0
        self.corpus_container["scores"] = self.corpus_container["scores"].astype("float32")
        self.store = None
        self.ranker = ranker
        if similarity_algorithm not in ["dot_product"]:
            ValueError(f"{self.similarity_algorithm} is not supported.")
        else:
            self.similarity_algorithm = similarity_algorithm
        self.k = k

    def get_vectorstore(self, embedding, building_params={"build": {"num_leaves": 2000, "num_leaves_to_search": 100, "training_sample_size": 250000}}):
        if self.similarity_algorithm == "dot_product":
            self.store = scann.scann_ops_pybind.builder(embedding, num_neighbors=self.k, distance_measure="dot_product")
        else:
            ValueError(f"{self.similarity_algorithm} is not supported.")
        self.store = self.store.tree(**building_params["build"])
        self.store = self.store.score_ah(dimensions_per_block=2, anisotropic_quantization_threshold=0.2)
        self.store = self.store.reorder(reordering_num_neighbors=100)
        self.store = self.store.build()

    def search(self, embedding, searching_params={"leaves_to_search": 150, "pre_reorder_num_neighbors": 250}):
        # transform (E) -> (1, E)
        if len(embedding.shape) == 1:
            embedding = embedding.reshape(1, -1)
        indicies, scores = self.store.search_batched(embedding, **searching_params)
        # normalize 0-1
        if self.similarity_algorithm == "dot_product":
            scores = ((scores + 1.0) / 2.0)
        # ranking
        return self.ranker(self.corpus_container, scores, indicies)
