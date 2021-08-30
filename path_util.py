#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
-----------------------------------------
@Author: zhaocy
@Email: 19110240027@fudan.edu.cn
@Created: 2019/12/17
------------------------------------------
@Modify: 2019/12/17
------------------------------------------
@Description:
"""
from pathlib import Path

from definitions import OUTPUT_DIR, DATA_DIR


class PathUtil:
    """
    provide a way to get a path to specific directive
    """

    @staticmethod
    def graph_data(pro_name, version):
        graph_data_output_dir = Path(DATA_DIR) / "graph" / pro_name
        graph_data_output_dir.mkdir(exist_ok=True, parents=True)

        graph_data_path = str(graph_data_output_dir / "{pro}.{version}.graph".format(pro=pro_name, version=version))
        return graph_data_path

    @staticmethod
    def doc_path(kno_type):
        doc_dir = Path(OUTPUT_DIR) / 'doc_for_similarity_model' / ('knowledge_' + str(kno_type))
        doc_dir.mkdir(parents=True, exist_ok=True)
        doc_path = str(doc_dir / "doc.collection")
        return doc_path

    # @staticmethod
    # def fast_text_data_dir(scenario_type):
    #     dir = Path(DATA_DIR) / "annotated_data" / "fast_text_data" / (
    #             "scenario_" + str(scenario_type))
    #     dir.mkdir(parents=True, exist_ok=True)
    #     return dir

    @staticmethod
    def avg_w2v_similarity_model_dir(kno_type):
        model_dir = Path(OUTPUT_DIR) / "avg_w2v_similarity_models" / ('knowledge_' + str(kno_type))
        return model_dir

    @staticmethod
    def tf_idf_similarity_model_dir(kno_type):
        model_dir = Path(OUTPUT_DIR) / "tf_idf_similarity_models" / ('knowledge_' + str(kno_type))
        return model_dir

    @staticmethod
    def pretrain_wiki_w2v():
        dir = Path(DATA_DIR) / "pretrain"
        dir.mkdir(exist_ok=True, parents=True)

        return str(dir / "pretrainwiki.100.w2v.bin")

    @staticmethod
    def tuned_word2vec():
        tuned_word2vec_dir = Path(OUTPUT_DIR) / "tuned_word2vec"
        tuned_word2vec_dir.mkdir(exist_ok=True, parents=True)

        tuned_word2vec_path = str(
            tuned_word2vec_dir / "so_api_post.tunrd.wordemb")

        return tuned_word2vec_path

    @staticmethod
    def doc_for_all_post():
        doc_for_all_post_dir = Path(OUTPUT_DIR) / "doc_for_all_post"
        doc_for_all_post_dir.mkdir(exist_ok=True, parents=True)

        doc_for_all_post_path = str(
            doc_for_all_post_dir / "so_api_post.doc.collection")

        return doc_for_all_post_path

    @staticmethod
    def pre_doc_for_all_post():
        doc_for_all_post_dir = Path(OUTPUT_DIR) / "doc_for_all_post"
        doc_for_all_post_dir.mkdir(exist_ok=True, parents=True)

        doc_for_all_post_path = str(
            doc_for_all_post_dir / "so_api_post.doc.pre.collection")

        return doc_for_all_post_path

    @staticmethod
    def fast_data_dir_for_sentence(kno_type=None):
        fast_text_data_dir = Path(DATA_DIR) / "fast_text_data"/("knowledge_"+str(kno_type))
        fast_text_data_dir.mkdir(exist_ok=True, parents=True)
        return str(fast_text_data_dir)

    @staticmethod
    def fast_data_dir_for_scenario(scenario_type=None):
        fast_data_dir_for_scenario = Path(DATA_DIR) / "fast_text_data_for_scenario"/("scenario_"+str(scenario_type))
        fast_data_dir_for_scenario.mkdir(exist_ok=True, parents=True)
        return str(fast_data_dir_for_scenario)

    @staticmethod
    def sentence_classifier_model_dir(kno_type=None):
        fast_data_model_dir = Path(OUTPUT_DIR) / "fast_text_model"/("knowledge_"+str(kno_type))
        fast_data_model_dir.mkdir(exist_ok=True, parents=True)
        return str(fast_data_model_dir)

    @staticmethod
    def scenario_classifier_model_dir(scenario_type=None):
        fast_data_model_dir = Path(OUTPUT_DIR) / "fast_text_model_for_scenario" / ("scenario_" + str(scenario_type))
        fast_data_model_dir.mkdir(exist_ok=True, parents=True)
        return str(fast_data_model_dir)

    @staticmethod
    def empirical_post_collection_path():
        so_post_dir = Path(DATA_DIR) / "so_post_collection"
        so_post_dir.mkdir(exist_ok=True, parents=True)

        so_post_path = str(
            so_post_dir / "sub_collection_for_empirical_study.bin")
        return so_post_path

    @staticmethod
    def data_expansion_collection_path():
        so_post_dir = Path(DATA_DIR) / "so_post"
        so_post_dir.mkdir(exist_ok=True, parents=True)

        so_post_path = str(
            so_post_dir / "sub_collection_for_data_expansion_study.bin")
        return so_post_path

    @staticmethod
    def linking_graph_path():
        graph_path = Path(DATA_DIR) / "android27_api.graph"
        return str(graph_path)

    @staticmethod
    def empirical_annotated_data_path():
        annotated_data_dir = Path(DATA_DIR) / "annotated_data"
        annotated_data_dir.mkdir(exist_ok=True, parents=True)

        annotated_data_path = str(
            annotated_data_dir / "processed_sentence_classified_data_xss_fix.json")
        return annotated_data_path
