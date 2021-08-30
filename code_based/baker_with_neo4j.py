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
import javalang
import re
import javalang.tree as Tree
from code_based.baker_without_ast_parser import BakerBasedWithoutParserSOPostAPILinker


class BakerBasedSOPostWithNeo4jAPILinker(BakerBasedWithoutParserSOPostAPILinker):
    """
    baker based on neo4j with ast parser
    """
    def baker(self, code):
        api_qualified_name = {}
        valid_code = self.recognize_valid_code(code)
        if valid_code is not None:
            code_blocks = self.recognize_code_block(valid_code)
            if len(code_blocks) > 0:
                for code_block in code_blocks:
                    if self.code_parser(code_block) is not None:
                        class_object_pair, class_method_dic = self.code_parser(code_block)
                        locate_class_method_dic = self.locate_api(code, class_method_dic)
                        api_qualified_name = self.linker(locate_class_method_dic, class_object_pair)
                    else:
                        super().baker(code)
            else:
                if self.code_parser(self.code_completion(valid_code)) is not None:
                    class_object_pair, class_method_dic = self.code_parser(self.code_completion(valid_code))
                    locate_class_method_dic = self.locate_api(code, class_method_dic)
                    api_qualified_name = self.linker(locate_class_method_dic, class_object_pair)
                else:
                    super().baker(code)
        else:
            print("invalid code, change to the baker without ast parser")
            super().baker(code)
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
            print('the code can not be parsed, change to the baker without ast parser')
            return
        return class_object_pair, class_method_dic
