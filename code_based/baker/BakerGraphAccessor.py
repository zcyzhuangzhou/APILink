#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
-----------------------------------------
@Author: zhaocy
@Email: 19110240027@fudan.edu.cn
@Created: 2020/2/17
------------------------------------------
@Modify: 2020/2/17
------------------------------------------
@Description: 
"""
from sekg.graph.accessor import GraphAccessor


class BakerGraphAccessor(GraphAccessor):
    def __init__(self, graph):
        super().__init__(graph)

    def get_all_in_relations(self, graph_id):
        query = 'match(n:entity) <-[r]- (m) where id(n) = %d return n.qualified_name, type(r), m.qualified_name limit 100' % graph_id
        r = self.graph.run(query).to_ndarray()[0:100]
        if r is None:
            print("no in relations")
            return None
        return r

    def get_all_out_relations(self, graph_id):
        query = 'match(n:entity) -[r]-> (m) where id(n) = %d return n.qualified_name, type(r), m.qualified_name limit 100' % graph_id
        r = self.graph.run(query).to_ndarray()[0:100]
        if r is None:
            print("no out relations")
            return None
        return r
