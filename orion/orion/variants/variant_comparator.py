import tempfile
from copy import copy
from enum import Enum

import graphviz
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt, image as mpimg
from pm4py import format_dataframe
from pm4py.algo.discovery.dfg.adapters.pandas import df_statistics
from pm4py.statistics.attributes.pandas import get as attributes_get
from pm4py.statistics.start_activities.pandas import get as sa_get
from pm4py.statistics.end_activities.pandas import get as ea_get
from pm4py.utils import INDEX_COLUMN
from pm4py.visualization.common import save
from pm4py.objects.conversion.log import converter as log_converter

from orion.variants import visualization
from orion.variants.plotting import categorical_edge_distribution_graph, continuous_edge_distribution_graph, \
    continuous_node_distribution_graph, categorical_node_distribution_graph
from orion.variants.statistics import do_mwu, do_chi_squared, do_wilcoxon
from orion.variants.preprocessing import prepare_dataframe_mean_per_activity_measurement, join_prepared_dataframes, \
    prepare_dataframe_mode_per_activity_measurement, prepare_dataframe_edges, prepare_dataframe_edges_categorical, \
    join_prepared_dataframes_on_edges, prepare_dataframe_edges_continuous
from orion.variants.visualization import node_mappings_from_gviz, gviz_to_html


class DataType(Enum):
    CONTINUOUS = 0
    CATEGORICAL = 1


def _filter_by_attributes(df, attributes):
    if attributes != "ALL":
        return df[df['variable'].isin(attributes)]
    return df


def _evaluate_statistical_test(test_results, sort_keys, sort_ascending):
    test_results["count_l"] = test_results.apply(lambda x: len(x["value_l"]), axis=1)
    test_results["count_r"] = test_results.apply(lambda x: len(x["value_r"]), axis=1)
    # bonferroni correction
    #test_results["p-val-threshold"] = test_results.apply(
    #    lambda x: 0.05 / max(1, min(len(x["value_l"]), len(x["value_r"]))),
    #    axis=1)
    #test_results = test_results[test_results["p-val"] < test_results["p-val-threshold"]]
    return test_results.sort_values(sort_keys, ascending=sort_ascending)



class VariantComparator:
    # needs values as expected by pm4py

    def __init__(self, case_id_column, activity_column, timestamp_column, attribute, operator, value, original, attribute_list_con, attribute_list_cat, dfg, variant1_name='variant 1', variant2_name='variant 2'):
        
        self.original = original
        self.case_id_column = case_id_column
        self.activity_column = activity_column
        self.timestamp_column = timestamp_column
        self.variant1_name = variant1_name
        self.variant2_name = variant2_name
        self.continuous_columns = attribute_list_con
        self.categorical_columns = attribute_list_cat

        if operator == "=":
            case_id_var_1 = self.original.loc[self.original[attribute] == value][self.case_id_column]
            case_id_var_2 = self.original.loc[self.original[attribute] != value][self.case_id_column]
        elif operator == ">":
            case_id_var_1 = self.original.loc[self.original[attribute] > value][self.case_id_column]
            case_id_var_2 = self.original.loc[self.original[attribute] <= value][self.case_id_column]
        elif operator == "<":
            case_id_var_1 = self.original.loc[self.original[attribute] < value][self.case_id_column]
            case_id_var_2 = self.original.loc[self.original[attribute] >= value][self.case_id_column]
        else:
            print("Unsupported operator provided. Please try again.")
        self.variant1 = self.original[self.original[self.case_id_column].isin(case_id_var_1)]
        self.variant2 = self.original[self.original[self.case_id_column].isin(case_id_var_2)]
        self.activity_comparison_results = {
            DataType.CONTINUOUS: None,
            DataType.CATEGORICAL: None
        }
        self.edge_comparison_results = {
            DataType.CONTINUOUS: None,
            DataType.CATEGORICAL: None
        }
        self.dfg = dfg
        self.node_id_mapping = {}

    def get_columns_for_type(self, data_type=DataType.CONTINUOUS, threshold=0.04, selected_attributes='ALL'):
        assert isinstance(data_type, DataType), "data type not supported. Use Continuous or Categorical"
        if data_type == DataType.CONTINUOUS:
            columns_for_type = self._get_continuous_columns()
        else:
            columns_for_type = self._get_categorical_columns()

        if selected_attributes == 'ALL':
            return self._sort_variables(columns_for_type)
        return self._sort_variables(list(set(columns_for_type) & set(selected_attributes)))

    def _get_categorical_columns(self):
        return self.categorical_columns

    def _get_continuous_columns(self):
        return self.continuous_columns

    def _build_dfg(self):
        # TODO: think about which variant to use?!
        if self.dfg is None:
            self.dfg = df_statistics.get_dfg_graph(self.original, measure="frequency")

    def _sort_variables(self, variables):
        return sorted(variables, key=str.casefold)

    def visualize(self, max_edges=20, output='html', attributes='ALL', data_type=DataType.CONTINUOUS,
                  data_type_threshold=0.04):
        attributes = self.get_columns_for_type(data_type, threshold=data_type_threshold, selected_attributes=attributes)

        self._build_dfg()

        activities_RBC = attributes_get.get_attribute_values(self.original, self.activity_column)
        for activity in activities_RBC:
            activities_RBC[activity] = self.most_significant_attribute_for_activity(activity,
                                                                                    attributes=attributes,
                                                                                    data_type=data_type)

        edges_RBC_diff = copy(self.dfg)
        for edge in edges_RBC_diff:
            edges_RBC_diff[edge] = self.most_significant_attribute_for_edge(edge,
                                                                            attributes=attributes,
                                                                            data_type=data_type)
        start_activities = sa_get.get_start_activities(self.original)
        end_activities = ea_get.get_end_activities(self.original)

        gviz = visualization.apply(self.dfg, activities_RBC=activities_RBC, edges_RBC=edges_RBC_diff,
                                   parameters={"start_activities": start_activities, "end_activities": end_activities,
                                               "maxNoOfEdgesInDiagram": max_edges})

        self.node_id_mapping = node_mappings_from_gviz(gviz)

        if output == 'plot':
            print(f"used attributes: {attributes}")

            fig = plt.figure(figsize=(15, 8))

            file_name = tempfile.NamedTemporaryFile(suffix='.png')
            file_name.close()

            save.save(gviz, file_name.name)

            img = mpimg.imread(file_name.name)
            plt.axis('off')
            plt.imshow(img)
            plt.show()

        elif output == 'html':
            return gviz_to_html(gviz)

    def _node_id_mapping(self, data_id):
        return self.node_id_mapping.get(data_id, None)

    def dataframe_for_node(self, data_id, attributes='ALL', data_type=DataType.CONTINUOUS,
                           data_type_threshold=0.04):
        attributes = self.get_columns_for_type(data_type, threshold=data_type_threshold, selected_attributes=attributes)

        node_name = self._node_id_mapping(data_id)
        if node_name:
            results_filtered = _filter_by_attributes(self.get_activity_comparison_results(data_type).reset_index(),
                                                     attributes)
            if data_type == DataType.CONTINUOUS:
                return self._readable_column_names(results_filtered[
                    results_filtered[self.activity_column] == node_name][
                    [self.activity_column, 'variable', 'p-val', 'RBC', 'count_l', 'count_r']].set_index(
                    [self.activity_column, 'variable']))
            else:
                return self._readable_column_names(results_filtered[
                    results_filtered[self.activity_column] == node_name][
                    [self.activity_column, 'variable', 'p-val', 'chi2', 'count_l', 'count_r']].set_index(
                    [self.activity_column, 'variable']))
        return "No Data"

    def dataframe_for_edge(self, data_id_left, data_id_right, attributes='ALL', data_type=DataType.CONTINUOUS,
                           data_type_threshold=0.04):
        attributes = self.get_columns_for_type(data_type, threshold=data_type_threshold, selected_attributes=attributes)

        node_name_left = self._node_id_mapping(data_id_left)
        node_name_right = self._node_id_mapping(data_id_right)
        if node_name_right and node_name_left:
            results_filtered = _filter_by_attributes(self.get_edge_comparison_results(data_type).reset_index(),
                                                     attributes)
            if data_type == DataType.CONTINUOUS:
                return self._readable_column_names(results_filtered[
                    (results_filtered[self.activity_column + '_l'] == node_name_left) &
                    (results_filtered[self.activity_column + '_r'] == node_name_right)][
                    [self.activity_column + '_l', self.activity_column + '_r', 'variable', 'p-val', 'RBC', 'count_l',
                     'count_r']].set_index(
                    [self.activity_column + '_l', self.activity_column + '_r', 'variable']))
            else:
                return self._readable_column_names(results_filtered[
                    (results_filtered[self.activity_column + '_l'] == node_name_left) &
                    (results_filtered[self.activity_column + '_r'] == node_name_right)][
                    [self.activity_column + '_l', self.activity_column + '_r', 'variable', 'p-val', 'chi2', 'count_l', 'count_r']].set_index(
                    [self.activity_column + '_l', self.activity_column + '_r', 'variable']))
        return "No Data"

    def plot_for_node_attribute(self, data_id, attribute, data_type=DataType.CONTINUOUS):
        node_name = self._node_id_mapping(data_id)
        if node_name:
            categorical_edges = self.get_activity_comparison_results(data_type).reset_index()
            comparison_attributes = categorical_edges[(categorical_edges[self.activity_column] == node_name) & (
                    categorical_edges['variable'] == attribute)]
            if comparison_attributes.size > 0:
                comparison_attributes = comparison_attributes.iloc[0]
                if data_type == DataType.CONTINUOUS:
                    return continuous_node_distribution_graph(comparison_attributes, attribute, self.variant1_name,
                                                              self.variant2_name)
                else:
                    return categorical_node_distribution_graph(comparison_attributes, attribute, self.variant1_name,
                                                               self.variant2_name)
        return "No Data"

    def plot_for_edge_attribute(self, data_id_left, data_id_right, attribute, data_type=DataType.CONTINUOUS):
        node_name_left = self._node_id_mapping(data_id_left)
        node_name_right = self._node_id_mapping(data_id_right)
        if node_name_right and node_name_left:
            categorical_edges = self.get_edge_comparison_results(data_type).reset_index()
            comparison_attributes = categorical_edges[(categorical_edges[self.activity_column + '_l'] == node_name_left) & (
                    categorical_edges[self.activity_column + '_r'] == node_name_right) & (
                                                              categorical_edges['variable'] == attribute)]
            if comparison_attributes.size > 0:
                comparison_attributes = comparison_attributes.iloc[0]
                if data_type == DataType.CONTINUOUS:
                    return continuous_edge_distribution_graph(comparison_attributes, attribute, self.variant1_name,
                                                              self.variant2_name)
                else:
                    return categorical_edge_distribution_graph(comparison_attributes, attribute, self.variant1_name,
                                                               self.variant2_name)
        return "No Data"

    def get_activity_comparison_results(self, data_type):
        #if data_type in self.activity_comparison_results and self.activity_comparison_results[data_type] is not None:
        #    return self.activity_comparison_results[data_type]
        #raise Exception('No results found')
    
        if data_type == "con":
            return self.activity_comparison_results[data_type]
        elif data_type == "cat":
            return self.activity_comparison_results[data_type]

    def _set_activity_comparison_results(self, data_type, results):
        #if data_type in self.activity_comparison_results:
        
        if data_type == DataType.CONTINUOUS:
            self.activity_comparison_results["con"] = results
        elif data_type == DataType.CATEGORICAL:
            self.activity_comparison_results["cat"] = results
        else:
            raise Exception('Can not set results')

    def get_edge_comparison_results(self, data_type):
        if data_type == "con":
            return self.edge_comparison_results[data_type]
        elif data_type == "cat":
            return self.edge_comparison_results[data_type]

    def _set_edge_comparison_results(self, data_type, results):
        #if data_type in self.edge_comparison_results:
        if data_type == DataType.CONTINUOUS:
            self.edge_comparison_results["con"] = results
        elif data_type == DataType.CATEGORICAL:
            self.edge_comparison_results["cat"] = results
        else:
            raise Exception('Can not set results')

    def do_activity_comparison(self, data_type=DataType.CONTINUOUS):
        assert isinstance(data_type, DataType), "data type not supported. Use Continuous or Categorical"
        if data_type == DataType.CONTINUOUS:
            self._do_activity_comparison_continuous()
        else:
            self._do_activity_comparison_categorical()

    def do_edge_comparison(self, data_type=DataType.CONTINUOUS):
        assert isinstance(data_type, DataType), "data type not supported. Use Continuous or Categorical"

        if data_type == DataType.CONTINUOUS:
            self._do_edge_comparison_continuous()
        else:
            self._do_edge_comparison_categorical()

    def most_significant_attribute_for_activity(self, activity, attributes='ALL', data_type=DataType.CONTINUOUS,
                                                data_type_threshold=0.04):
        attributes = self.get_columns_for_type(data_type, threshold=data_type_threshold, selected_attributes=attributes)

        df_mwu = self.get_activity_comparison_results(data_type).reset_index()
        df_mwu = _filter_by_attributes(df_mwu, attributes)
        top_mwu = df_mwu.groupby(self.activity_column).head(1)
        res = top_mwu.reset_index().loc[top_mwu.reset_index()[self.activity_column] == activity, "res"]
        if len(res.values) > 0:
            return res.values[0]
        else:
            return 0

    def most_significant_attribute_for_edge(self, edge, attributes='ALL', data_type=DataType.CONTINUOUS,
                                            data_type_threshold=0.04):
        attributes = self.get_columns_for_type(data_type, threshold=data_type_threshold, selected_attributes=attributes)

        df_mwu = self.get_edge_comparison_results(data_type).reset_index()
        df_mwu = _filter_by_attributes(df_mwu, attributes)
        top_mwu = df_mwu.groupby([self.activity_column + "_l", self.activity_column + "_r"]).head(1)
        res = top_mwu.reset_index().loc[
            (top_mwu.reset_index()[self.activity_column + "_l"] == edge[0]) & (top_mwu.reset_index()[self.activity_column + "_r"] == edge[
                1]), "res"]
        if len(res.values) > 0:
            return res.values[0]
        else:
            return 0

    def _do_activity_comparison_continuous(self):
        # run mann-whitney u test
        self._set_activity_comparison_results(DataType.CONTINUOUS,
                                              self._do_statistical_test(
                                                  prepare_func=prepare_dataframe_mean_per_activity_measurement,
                                                  test_func=do_mwu,
                                                  sort_keys=[self.activity_column, "RBC_abs"], sort_ascending=False))

    def _do_activity_comparison_categorical(self):
        # run chi-squared test
        self._set_activity_comparison_results(DataType.CATEGORICAL,
                                              self._do_statistical_test(
                                                  prepare_func=prepare_dataframe_mode_per_activity_measurement,
                                                  test_func=do_chi_squared,
                                                  sort_keys=[self.activity_column, "p-val"], sort_ascending=True))

    def _do_edge_comparison_continuous(self):
        # run wilcoxon test
        self._set_edge_comparison_results(DataType.CONTINUOUS,
                                          self._do_statistical_test(prepare_func=prepare_dataframe_edges_continuous,
                                                                    test_func=do_mwu,
                                                                    join_variants=True,
                                                                    join_func=join_prepared_dataframes_on_edges,
                                                                    sort_keys=[self.activity_column + "_l", self.activity_column + "_r",
                                                                               "RBC_abs"],
                                                                    sort_ascending=False)
                                          )

    def _do_edge_comparison_categorical(self):
        self._set_edge_comparison_results(DataType.CATEGORICAL,
                                          self._do_statistical_test(prepare_func=prepare_dataframe_edges_categorical,
                                                                    test_func=do_chi_squared,
                                                                    join_variants=True,
                                                                    join_func=join_prepared_dataframes_on_edges,
                                                                    sort_keys=[self.activity_column + "_l", self.activity_column + "_r",
                                                                               "p-val"],
                                                                    sort_ascending=False)
                                          )

    def _do_statistical_test(self, prepare_func, test_func, sort_keys, sort_ascending, join_variants=True,
                             join_func=join_prepared_dataframes):
        variant1_prepared = prepare_func(self.variant1, self.case_id_column, self.activity_column, self.continuous_columns, self.categorical_columns)
        variant2_prepared = prepare_func(self.variant2, self.case_id_column, self.activity_column, self.continuous_columns, self.categorical_columns)
        if join_variants:
            variants_joined = join_func(variant1_prepared, variant2_prepared, self.activity_column)
            test_results = variants_joined.apply(test_func, axis=1)
            return _evaluate_statistical_test(test_results, sort_keys, sort_ascending)
        else:
            test_results = []
            for var in [variant1_prepared, variant2_prepared]:
                test_results.append(
                    _evaluate_statistical_test(var.apply(test_func, axis=1), sort_keys, sort_ascending))
            return test_results

    def _readable_column_names(self, df):
        col_names = {
            'count_l': f'Count {self.variant1_name}',
            'count_r': f'Count {self.variant2_name}',
            'p-val_1': f'P-value {self.variant1_name}',
            'p-val_2': f'P-value {self.variant2_name}',
            'RBC_1': f'RBC {self.variant1_name}',
            'RBC_2': f'RBC {self.variant2_name}',
            'count_1': f'Count {self.variant1_name}',
            'count_2': f'Count {self.variant2_name}',
            self.activity_column + '_l': f'',
            self.activity_column + '_r': f'',
            'variable': f'Measurement',
            'p-val': f'P-value',
        }
        return df.rename(columns=col_names)

    def prepare(self):
        # continuous vars
        self.do_activity_comparison(DataType.CONTINUOUS)
        self.do_edge_comparison(DataType.CONTINUOUS)
        # categorical vars
        self.do_activity_comparison(DataType.CATEGORICAL)
        self.do_edge_comparison(DataType.CATEGORICAL)

    @staticmethod
    def format_df(df, case_id, activity_key, timestamp_key):
        return format_dataframe(df, case_id=case_id, activity_key=activity_key, timestamp_key=timestamp_key) \
            .set_index(INDEX_COLUMN)
