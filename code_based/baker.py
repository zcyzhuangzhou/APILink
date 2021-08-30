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
from sekg.graph.exporter.graph_data import GraphData
from sekg.util.code import CodeElementNameUtil
import javalang
import re
import javalang.tree as Tree


class BakerBasedSOPostAPILinker:
    """
    baker based on graph with ast parser
    """
    def __init__(self, graph_path):
        self.qualified_name_set = set()
        self.long_name_dic = {}
        self.short_name_dic = {}
        self.CODE_NAME_UTIL = CodeElementNameUtil()
        self.api_graph = None
        self.init_from_graph_data(graph_path)

    def init_from_graph_data(self, graph_path):
        self.api_graph: GraphData = GraphData.load(graph_path)
        self.init_api_table()

    def init_api_table(self,):
        api_node_ids = self.api_graph.get_node_ids_by_label("class")
        api_node_ids.update(self.api_graph.get_node_ids_by_label("method"))
        api_node_ids.update(self.api_graph.get_node_ids_by_label("interface"))
        for node_id in api_node_ids:
            api_node = self.api_graph.get_node_info_dict(node_id)
            qualified_name = api_node["properties"]["qualified_name"]
            # 將qualified name的處理結果保存，後面直接引用，和後面直接再次處理，那個比較合適
            long_name, short_name, parameter_list = self.process_api(qualified_name)

            self.qualified_name_set.add(qualified_name)

            if long_name not in self.long_name_dic.keys():
                self.long_name_dic[long_name] = {qualified_name}
            else:
                self.long_name_dic[long_name].add(qualified_name)

            if short_name not in self.short_name_dic.keys():
                self.short_name_dic[short_name] = {qualified_name}
            else:
                self.short_name_dic[short_name].add(qualified_name)

    def baker(self, code):
        api_qualified_name = {}
        class_object_pair = {}
        class_method_dic = {}
        valid_code = self.recognize_valid_code(code)
        if valid_code is not None:
            code_blocks = self.recognize_code_block(valid_code)
            if len(code_blocks) > 0:
                for code_block in code_blocks:
                    class_object_pair, class_method_dic = self.code_parser(code_block)
            else:
                class_object_pair, class_method_dic = self.code_parser(self.code_completion(valid_code))
            locate_class_method_dic = self.locate_api(code, class_method_dic)
            api_qualified_name = self.linker(self.api_graph, locate_class_method_dic, class_object_pair)
        else:
            print("invalid code")
        return api_qualified_name

    def recognize_valid_code(self, code):
        """
        去除code中的注释
        :param code: 原始代码片段
        :return: 修改后的合法代码片段
        """
        self.pattern_line = "\/\/[^\n]*"
        self.pattern_block = "\/\*(\s|.)*?\*\/"
        self.pattern_code = re.compile("[a-zA-Z0-9_ ]")
        self.pattern_method = re.compile("\([^()]+\)")
        self.pattern_parameter = re.compile('([a-zA-Z0-9_ ]+)([^a-zA-Z0-9_ ])')
        try:
            code = re.sub(self.pattern_line, '', code, flags=re.I)
            code = re.sub(self.pattern_block, '', code, flags=re.M)
            code = re.sub("\n[\s]*\n", '\n', code, flags=re.I)
        except Exception as e:
            print(str(e))
        code_lines = code.split('\n')
        # 去除code_lines中的空格和import语句
        code_lines = list(filter(lambda x: x != '' and not x.isspace() and not x.startswith('import'), code_lines))

        for code_line in code_lines:
            if code_line.__contains__('...'):
                return
            elif code_line.strip()[-1] not in ['{', '}', ')', ';'] and code_line.strip()[0] not in ['@']:
                return
            elif code_line.strip()[-1] in ['{', '}', ')', ';'] and not self.pattern_code.match(code_line) and not code_line.strip()[0] in ['{', '}', ')', ';']:
                return
        for index, code_line in enumerate(code_lines.copy()):
            if not code_line.startswith('if') and code_line.endswith(')'):
                code_lines[index] = code_lines[index] + ';'
            results = self.pattern_method.findall(code_line)
            if len(results) > 0:
                for i, result in enumerate(results.copy()):
                    parameters = result.lstrip('(').rstrip(')').split(',')
                    for j, parameter in enumerate(parameters.copy()):
                        if self.pattern_parameter.search(parameter) is not None:
                            parameters[j] = self.pattern_parameter.search(parameter).group(1)
                        else:
                            parameters[j] = parameter
                    results[i] = ','.join(parameters)
                    results[i] = '(' + results[i] + ')'
                    code_lines[index] = code_lines[index].replace(result, results[i])
        code = '\n'.join(code_lines)
        return code

    def recognize_code_block(self, code):
        code_blocks = []
        code_lines = code.split('\n')
        line_index = 0
        while line_index < len(code_lines):
            if code_lines[line_index].__contains__('class ' or 'interface '):
                start_index = line_index
                brackets = []
                if code_lines[line_index].__contains__('{' and '}'):
                    code_blocks.append(code_lines[line_index])
                    line_index = line_index + 1
                    continue
                if code_lines[line_index].__contains__('{'):
                    brackets.append("{")
                line_index = line_index + 1
                if line_index >= len(code_lines):
                    break
                code = ''
                while True:
                    if code_lines[line_index].__contains__('{'):
                        brackets.append('{')
                    if code_lines[line_index].__contains__('}'):
                        brackets.pop()
                    end_index = line_index + 1
                    line_index = line_index + 1
                    if len(brackets) <= 0:
                        break
                    if line_index >= len(code_lines):
                        break
                for code_index in range(start_index, end_index):
                    code = code + code_lines[code_index] + '\n'
                code_blocks.append(code)
            line_index = line_index + 1
        return code_blocks

    def recognize_method_signature(self, code):
        method_signature_patterns = [
            re.compile(
                r'(public |private |protected )(void |abstract |static |final |native |synchronized )?[a-zA-Z0-9_ ]+(\([a-zA-Z0-9_, ]*\))')
        ]
        code_lines = code.split('\n')
        for code_line in code_lines:
            for index, pattern in enumerate(method_signature_patterns):
                search_rs = pattern.match(code_line)
                if search_rs is not None:
                    return True
        return False

    def code_completion(self, code):
        if self.recognize_method_signature(code):
            return "public class DummyClass{\n" + code + "\n }"
        else:
            return "public class DummyClass{\n" + " public void dummyMethod(){\n" + code + " }\n" + "}"

    def code_parser(self, code):
        class_object_pair = {}
        class_method_dic = {}
        class_extends_implements = ''
        try:
            tree = javalang.parse.parse(code)
            class_trees = tree.types
            for class_tree in class_trees:
                for path, node in class_tree:
                    # print(node)
                    if isinstance(node, Tree.ClassDeclaration):
                        if node.extends is not None:
                            class_extends_implements = node.extends.name
                            class_method_dic[class_extends_implements] = []
                        elif node.implements is not None:
                            class_extends_implements = node.implements.name
                            class_method_dic[class_extends_implements] = []
                    elif isinstance(node, Tree.MethodDeclaration):
                        if node.annotations is not None:
                            for annotation in node.annotations:
                                if annotation.name == 'Override':
                                    class_method_dic.setdefault(class_extends_implements, []).append(node.name)
                    elif isinstance(node, Tree.SuperMethodInvocation):
                        class_method_dic.setdefault(class_extends_implements, []).append(node.member)
                    elif isinstance(node, Tree.ClassCreator):
                        class_method_dic[node.type.name] = []
                    elif isinstance(node, Tree.LocalVariableDeclaration):
                        for declarator in node.declarators:
                            class_object_pair.setdefault(node.type.name, []).append(declarator.name)
                        class_method_dic[node.type.name] = []
                    elif isinstance(node, Tree.ReferenceType):
                        if node.name not in class_method_dic.keys():
                            class_method_dic[node.name] = []
                    elif isinstance(node, Tree.MethodInvocation) and node.qualifier is not None:
                        if len(class_object_pair) > 0:
                            for class_object_pair_value in class_object_pair.values():
                                if node.qualifier in class_object_pair_value:
                                    class_method_dic.setdefault(list(class_object_pair.keys())[
                                                                         list(class_object_pair.values()).index(
                                                                             class_object_pair_value)], []).append(
                                        node.member)
                                else:
                                    class_method_dic.setdefault(node.qualifier, []).append(node.member)
                        else:
                            class_method_dic.setdefault(node.qualifier, []).append(node.member)
                        if node.selectors is not None:
                            for selector in node.selectors:
                                class_method_dic.setdefault(node.qualifier + '.' + node.member, []).append(
                                    selector.member)
            print("类和对象配对:", class_object_pair)
            print("javalang解析:", class_method_dic)
        except Exception as e:
            print('%' * 20)
            print(code)
            print('%' * 20)
        return class_object_pair, class_method_dic

    def locate_api(self, code, class_method_dic):
        locate_class_method_dic = {}
        for key in class_method_dic.keys():
            tmp_method = []
            new_key = key + str([m.span() for m in re.finditer(key, code)])
            locate_class_method_dic.setdefault(new_key, [])
            for value in class_method_dic[key]:
                if value not in tmp_method:
                    indexes = [m.span() for m in re.finditer(value, code)]
                    if len(indexes) > 1:
                        tmp_method.append(value)
                        for index in indexes:
                            new_value = str(value) + '[' + str(index) + ']'
                            locate_class_method_dic.setdefault(new_key, []).append(new_value)
                    else:
                        locate_class_method_dic.setdefault(new_key, []).append(str(value) + str(indexes))
        print("locate信息: ", locate_class_method_dic)
        return locate_class_method_dic

    def linker(self, api_graph, locate_class_method_dic, class_object_pair):
        api_qualified_name = {}
        locate_class_apis = locate_class_method_dic.keys()
        for locate_class_api in locate_class_apis:
            class_api = locate_class_api.split('[')[0]
            if not class_api.__contains__('.'):
                locate_method_apis = locate_class_method_dic[locate_class_api]
                simple_methods = []
                for locate_method_api in locate_method_apis:
                    method_api = locate_method_api.split('[')[0]
                    simple_methods.append(self.CODE_NAME_UTIL.simplify(method_api))
                # qualified name完全匹配--严格匹配
                if class_api in self.qualified_name_set:
                    api_qualified_name[locate_class_api] = class_api
                    for index, locate_method_api in enumerate(locate_method_apis):
                        api_qualified_name[locate_method_api] = class_api + '.' + locate_method_api.split('[')[0]
                    continue
                candidate_classes = set()
                if class_api in self.short_name_dic:
                    candidate_classes.update(self.short_name_dic[class_api])
                if class_api in self.long_name_dic:
                    candidate_classes.update(self.long_name_dic[class_api])
                tmp_api_qualified_name = dict()
                for candidate_class in candidate_classes:
                    candidate_class_node = api_graph.find_one_node_by_property("qualified_name", candidate_class)
                    if candidate_class_node is None:
                        continue
                    node_id = candidate_class_node['id']
                    in_relations_tuples = api_graph.get_all_in_relations(node_id)
                    all_methods = []
                    for in_relations_tuple in in_relations_tuples:
                        if in_relations_tuple[1] == 'belong to':
                            all_methods.append(
                                api_graph.get_node_info_dict(in_relations_tuple[0])["properties"]["qualified_name"])
                    all_simple_methods = []
                    for all_method in all_methods:
                        all_simple_methods.append(self.CODE_NAME_UTIL.simplify(all_method))
                    if set(simple_methods) < set(all_simple_methods):
                        tmp_api_qualified_name.setdefault(candidate_class, [])
                        for simple_method in simple_methods:
                            tmp_api_qualified_name.setdefault(candidate_class, []).append(
                                candidate_class + '.' + simple_method)
                if len(tmp_api_qualified_name) == 1:
                    class_qualified_name = list(tmp_api_qualified_name.keys())[0]
                    method_qualified_name = tmp_api_qualified_name[class_qualified_name]
                    api_qualified_name[locate_class_api] = class_qualified_name
                    for index, locate_method_api in enumerate(locate_method_apis):
                        api_qualified_name[locate_method_api] = method_qualified_name[index]
            else:
                object_name = class_api.split('.')[0]
                class_name = ''
                qualified_names = set()
                for key in class_object_pair.keys():
                    if object_name in class_object_pair[key]:
                        class_name = key
                for key in api_qualified_name.keys():
                    if key.__contains__(class_name):
                        return_value_type_name = api_qualified_name[key] + '.' + class_api.split('.')[1]
                        if return_value_type_name in self.short_name_dic:
                            qualified_names = self.short_name_dic[return_value_type_name]
                        if return_value_type_name in self.long_name_dic:
                            qualified_names = self.long_name_dic[return_value_type_name]
                        first_flag = False
                        for qualified_name in qualified_names:
                            api_node = api_graph.find_one_node_by_property("qualified_name", qualified_name)
                            node_id = api_node['id']
                            out_relations_tuples = api_graph.get_all_out_relations(node_id)
                            for out_relations_tuple in out_relations_tuples:
                                if out_relations_tuple[1] == 'return value type' or out_relations_tuple[1] == 'has return value':
                                    first_flag = True
                                    return_value_type = api_graph.get_node_info_dict(out_relations_tuple[2])["properties"]["qualified_name"]
                                    for method_name in locate_class_method_dic[locate_class_api]:
                                        api_qualified_name[method_name] = str(return_value_type) + '.' + str(method_name.split('[')[0])
                                    break
                            if first_flag:
                                break
                        break
        print("baker链接: ", api_qualified_name)
        return api_qualified_name

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
