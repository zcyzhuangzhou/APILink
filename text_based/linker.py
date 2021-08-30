#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
-----------------------------------------
@Author: zhaocy
@Email: 19110240027@fudan.edu.cn
@Created: 2019/11/20
------------------------------------------
@Modify: 2019/11/20
------------------------------------------
@Description:
"""
import difflib
from pathlib import Path
from sekg.graph.exporter.graph_data import GraphData
from definitions import DATA_DIR
from model.base import SOPost
from path_util import PathUtil


class TextBasedSOPostAPILinker:
    def __init__(self):
        self.qualified_name_set = set()
        self.long_name_dic = {}
        self.short_name_dic = {}
        self.qualified_name_2_process_api_result = {}
        self.init_api_table()

    def init_api_table(self):
        api_graph: GraphData = GraphData.load(PathUtil.linking_graph_path())
        api_node_ids = api_graph.get_node_ids_by_label("class")
        api_node_ids.update(api_graph.get_node_ids_by_label("method"))
        api_node_ids.update(api_graph.get_node_ids_by_label("interface"))
        for node_id in api_node_ids:
            api_node = api_graph.get_node_info_dict(node_id)
            qualified_name = api_node["properties"]["qualified_name"]
            # 將qualified name的處理結果保存，後面直接引用，和後面直接再次處理，那個比較合適
            long_name, short_name, parameter_list = self.process_api(qualified_name)
            self.qualified_name_2_process_api_result[qualified_name] = {"long_name": long_name,
                                                                        "short_name": short_name,
                                                                        "parameter_list": parameter_list}
            self.qualified_name_set.add(qualified_name)

            if long_name not in self.long_name_dic.keys():
                self.long_name_dic[long_name] = {qualified_name}
            else:
                self.long_name_dic[long_name].add(qualified_name)

            if short_name not in self.short_name_dic.keys():
                self.short_name_dic[short_name] = {qualified_name}
            else:
                self.short_name_dic[short_name].add(qualified_name)

    def link_one(self, post: SOPost, api):
        """
        try to link one api
        :param post:
        :param api: the api need to linked
        :return:
        """
        long_name, short_name, parameter_list = self.process_api(api)
        # qualified name完全匹配--严格匹配
        if api in self.qualified_name_set:
            return api
        # long name相同看参数类型和数目--严格匹配
        if long_name in self.long_name_dic.keys():
            long_name_set = self.long_name_dic[long_name]
            score_dic = {}
            for qualified_name in long_name_set:
                if not parameter_list:
                    score_dic[qualified_name] = 0
                    continue
                # qualified_long_name = self.qualified_name_2_process_api_result[qualified_name]["long_name"]
                # qualified_short_name = self.qualified_name_2_process_api_result[qualified_name]["short_name"]
                parameter_list_for_qualified_name = self.qualified_name_2_process_api_result[qualified_name][
                    "parameter_list"]
                # qualified_long_name, qualified_short_name, parameter_list_for_qualified_name = self.process_api(
                #     qualified_name)
                if len(parameter_list_for_qualified_name) != len(parameter_list):
                    score_dic[qualified_name] = 0
                    continue
                score = len(set(parameter_list) & set(parameter_list_for_qualified_name)) / len(parameter_list)
                score_dic[qualified_name] = score
            score_result = sorted(score_dic.items(), key=lambda x: x[1], reverse=True)
            return score_result[0][0]
        # 模糊匹配，首先匹配long name,其次匹配short name，然後是參數个数，最後是參數相似度
        if short_name in self.short_name_dic.keys():
            short_name_set = self.short_name_dic[short_name]
            score_dic = {}
            for qualified_name in short_name_set:
                para_num = len(parameter_list)
                qualified_long_name = self.qualified_name_2_process_api_result[qualified_name]["long_name"]
                qualified_short_name = self.qualified_name_2_process_api_result[qualified_name]["short_name"]
                parameter_list_for_qualified_name = self.qualified_name_2_process_api_result[qualified_name][
                    "parameter_list"]
                # qualified_long_name, qualified_short_name, parameter_list_for_qualified_name = self.process_api(
                #     qualified_name)
                score_long = self.string_similar(qualified_long_name, long_name)
                score_short = self.string_similar(qualified_short_name, short_name)
                score_para = 0
                if parameter_list:
                    score_para = len(set(parameter_list) & set(parameter_list_for_qualified_name)) / len(parameter_list)
                    para_num = abs(para_num - len(parameter_list_for_qualified_name))
                score_dic[qualified_name] = [score_long, score_short, para_num, score_para]
            score_result = sorted(score_dic.items(), key=lambda x: (x[1][0], x[1][1], x[1][2], x[1][3]), reverse=True)
            return score_result[0][0]
        return api

    def link_batch(self, post: SOPost, apiList):
        """
        try to link one api
        :param post:
        :param api: the api need to linked
        :return:
        """
        # todo: need to implement
        apiReturn = set()
        for api in apiList:
            apiLink = self.link_one(post, api)
            apiReturn.add(apiLink)
        return apiReturn

    def string_similar(self, s1, s2):
        s1 = s1.lower()
        s2 = s2.lower()
        return difflib.SequenceMatcher(None, s1, s2).quick_ratio()

    def process_api(self, api):
        api_split_parentheses = api.split("(")
        long_name = api_split_parentheses[0].strip()
        short_name = long_name.split(".")[-1].strip()
        parameter_list_for_api = []
        if "(" in api and ")" in api:
            parameter_list_for_api = api_split_parentheses[1].split(")")[0].strip().split(",")
        parameter_list_result = []
        for item in parameter_list_for_api:
            item = item.strip()
            if item:
                p = item.split(" ")[0]
                parameter_list_result.append(p)
        return long_name, short_name, parameter_list_result
