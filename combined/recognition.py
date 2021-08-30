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
@Description: extract the API mentioned in the SO post from the code.
"""
import os
import zipfile
from pathlib import Path
from xml.etree.ElementTree import parse
from base import SOPostAPIRecognition
from code_based.recognition import CodeBasedSOPostAPIRecognition
from text_based.recognition import TextBasedSOPostAPIRecognition
from model.base import SOPost


class CombinedSOPostAPIRecognition(SOPostAPIRecognition):
    JAVA_KEY_WORDS = ["abstract", "assert", "boolean", "break", "byte", "case", "catch", "char", "class", "const",
                      "continue", "default", "do", "double", "else", "enum", "extends", "final", "finally", "float",
                      "for", "goto", "if", "implements", "import", "instanceof", "int", "interface", "long", "native",
                      "new", "package", "private", "protected", "public", "return", "strictfp", "short", "static",
                      "super", "switch", "synchronized", "this", "throw", "throws", "transient", "try", "void",
                      "volatile", "while"]
    ORI_API_FILTER_WORDS = ["returns", "within", "data", "array", "call", "html", "util", "type", "comp.lang.java.help"]
    QUALIFIED_NAME_FILTER_WORDS = ["javax.xml.crypto.Data", "java.sql.Array"]

    def __init__(self, graph, graph_client):
        self.text_recognizer = TextBasedSOPostAPIRecognition()
        self.code_recognizer = CodeBasedSOPostAPIRecognition(graph=graph, graph_client=graph_client)
        self.so_tag_list = list(self.__int_tags().keys())

    def __int_tags(self):
        so_path = os.path.dirname(os.path.abspath(__file__))
        tag_path = str(Path(so_path) / "stackoverflow.com-Tags.zip")
        if os.path.exists(tag_path):
            with zipfile.ZipFile(tag_path, 'r') as z:
                f = z.open('Tags.xml')
            doc = parse(f)
            root = doc.getroot()
            tag_data = []
            for child in root:
                tag_data.append(child.attrib)
            tag_dic = {}
            for item in tag_data:
                tag_dic[item["TagName"].lower()] = item
            return tag_dic
        else:
            return {}

    def recognize(self, post: SOPost, is_completed=True):
        """
        return list of APIs
        :param post:
        :param is_completed, whether complete the API into qualified name as much as possible
        :return:
        """
        apis = []
        if post is None:
            return apis
        api_from_text = self.text_recognizer.recognize(post, is_completed)
        api_from_code = []
        try:
            api_from_code = self.code_recognizer.recognize(post, is_completed)
        except Exception as e:
            print(e)
        if not api_from_text:
            apis = api_from_code
            apis = self.filter_api(apis)
            return apis
        if not api_from_code:
            apis = api_from_text
            apis = self.filter_api(apis)
            return apis
        same_api_index = []
        for api_text in api_from_text:
            for index, api_code in enumerate(api_from_code):
                if api_text["ori_api"] == api_code["ori_api"] and api_text["qualified_name"] == api_code["qualified_name"]:
                    apis.append({"ori_api": api_text["ori_api"],
                                 "qualified_name": api_text["qualified_name"],
                                 "alias": api_text["alias"],
                                 "sentence": api_text["sentence"] + api_code["sentence"],
                                 "processed_sentence": api_text["processed_sentence"] + api_code["processed_sentence"]})
                    same_api_index.append(index)
                    break
                elif index == len(api_from_code) - 1:
                    apis.append(api_text)
        for index, api_code in enumerate(api_from_code):
            if index not in same_api_index:
                apis.append(api_code)
        apis = self.filter_api(apis)
        return apis

    def filter_api(self, apis):
        if not apis:
            return apis
        new_apis = []
        for item in apis:
            if len(item["ori_api"]) < 3 or item["ori_api"] in self.JAVA_KEY_WORDS or len(item["ori_api"].split("(")[0]) < 3:
                continue
            if item["ori_api"].lower() in self.so_tag_list:
                continue
            if item["ori_api"].endswith('.java') or item["ori_api"].endswith('.class') or item["ori_api"].endswith('.org'):
                continue
            if item["ori_api"].lower() in self.ORI_API_FILTER_WORDS or item["qualified_name"] in self.QUALIFIED_NAME_FILTER_WORDS:
                continue
            if item["ori_api"].endswith('.html') or item["ori_api"].endswith('.json') or item["ori_api"].endswith('.txt'):
                continue
            if item["qualified_name"].startswith("java.awt.List"):
                new_apis.append({"ori_api": item["ori_api"],
                                 "qualified_name": item["qualified_name"].replace("java.awt.List", "java.util.List"),
                                 "alias": item["alias"],
                                 "sentence": item["sentence"],
                                 "processed_sentence": item["processed_sentence"]})
            new_apis.append(item)
        return new_apis
