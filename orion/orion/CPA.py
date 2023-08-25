import pandas as pd
import numpy as np
from scipy import stats
from statsmodels.stats import multitest
import warnings
warnings.filterwarnings("ignore")

from orion.data_preparation import LogPreprocessor 
from orion.attribute_classification import AttributeClassifier
from orion.change_detection import ChangeDetector
from orion.relationship_detection import RelationshipDetector
from orion.variants.variant_comparator import VariantComparator

class CPA:

    def __init__(self, source_df, case_id_column, activity_column, time_column, columns_to_drop):
        self.source_df = source_df
        self.source_df = self.source_df.drop(columns_to_drop, axis=1)
        self.case_id_column = case_id_column
        self.activity_column = activity_column
        self.time_column = time_column
        self.data_preprocessor = LogPreprocessor(self.source_df, case_id_column=self.case_id_column, activity_column=self.activity_column, 
                                                 timestamp_column=self.time_column)
        self.event_log = self.data_preprocessor.event_log
        self.dfg = self.data_preprocessor.dfg
        self.efg = self.data_preprocessor.efg
        self.repetition_scores = self.data_preprocessor.repetition_scores
        self.repetition_scores = self.repetition_scores.sort_values("repetition_score",ascending=False)

    # API calls

    # context-aware 

    def set_recurring_activities(self, selected_activities: list):
        self.recurring_activities = selected_activities
        self.data_preprocessor.recurring_activities = selected_activities

    def identify_context(self, lambd, ignore_activities: list):
        self.data_preprocessor.identify_context(lambd, ignore_activities)
        self.mapping_before = self.data_preprocessor.mapping_before
        self.mapping_after = self.data_preprocessor.mapping_after

    def transform_event_log(self):
        self.data_preprocessor.transform_event_log()
        self.source_df = self.data_preprocessor.source_df
        self.dfg = self.data_preprocessor.dfg
        self.efg = self.data_preprocessor.efg
        self.event_log = self.data_preprocessor.event_log


    # add variants to df
    def add_variants(self):
        self.df_with_variants = self.data_preprocessor.add_variants()

    # dynamic event attributes and con/cat classification
    def prepare_attribute_classification(self):
        self.attribute_classifier = AttributeClassifier(self.source_df, self.case_id_column, self.activity_column, self.time_column)
        self.att_matrix = self.attribute_classifier.compute_attribute_matrix()
        self.classification_scores_con_cat = self.attribute_classifier.compute_classification_scores_con_cat()
        self.attribute_classifier.classify_dynamic_attribute(self.classification_scores_con_cat)

    # manual adjustment in tool
    def classify_attribute_type(self, attribute_threshold):
        self.attribute_classifier.classifiy_con_cat(self.classification_scores_con_cat, attribute_threshold)

    def compute_con_cat_attribute_list(self):
        classification_scores_con_cat = self.classification_scores_con_cat.copy()
        classification_scores_con_cat = classification_scores_con_cat.reset_index()
        classification_scores_con_cat = classification_scores_con_cat.rename({"index":"Attribute"}, axis=1)
        self.attribute_list_con = list(classification_scores_con_cat.loc[(classification_scores_con_cat["class"] == "dynamic") & 
                                                                         (classification_scores_con_cat["type"] == "continuous")]["Attribute"])
        self.attribute_list_cat = list(classification_scores_con_cat.loc[(classification_scores_con_cat["class"] == "dynamic") & 
                                                                         (classification_scores_con_cat["type"] == "categorical")]["Attribute"])
    # efg/dfg filtering

    def filter_dfg(self, sample_threshold):
        dfg_to_drop = list()
        for rel in self.dfg:
            if (self.dfg[rel] <= sample_threshold):
                dfg_to_drop.append(rel)
        for rel in dfg_to_drop:
            del(self.dfg[rel])  
    
    def filter_efg(self, sample_threshold):
        efg_to_drop = list()
        for rel in self.efg:
            if (self.efg[rel] <= sample_threshold):
                efg_to_drop.append(rel)
        for rel in efg_to_drop:
            del(self.efg[rel])      

    # Change Pattern Detection

    def initialize_change_pattern_detection(self):
        self.change_detector = ChangeDetector(self.df_with_variants, self.case_id_column, self.activity_column, self.time_column, 
                                              self.attribute_list_con, self.attribute_list_cat, self.att_matrix, self.dfg, self.efg)
        self.df_con = pd.DataFrame()
        self.df_cat = pd.DataFrame()

    def detect_continuous_change_patterns_dfg(self):
        self.change_detector.detect_continuous_changes_in_dfg()
        self.df_con = self.change_detector.df_con
        try:
            self.df_con = self.df_con.loc[~self.df_con["P"].isna()]
        except:
            pass

    def detect_continuous_change_patterns_efg(self):
        self.change_detector.detect_continuous_changes_in_efg()
        self.df_con = self.change_detector.df_con
        try:
            self.df_con = self.df_con.loc[~self.df_con["P"].isna()]
        except:
            pass
    def detect_categorical_change_patterns_dfg(self):
        self.change_detector.detect_categorical_changes_in_dfg()
        self.df_cat = self.change_detector.df_cat
        try:
            self.df_cat = self.df_cat.loc[~self.df_cat["P"].isna()]
        except:
            pass
    def detect_categorical_change_patterns_efg(self):
        self.change_detector.detect_categorical_changes_in_efg()
        self.df_cat = self.change_detector.df_cat
        try:
            self.df_cat = self.df_cat.loc[~self.df_cat["P"].isna()]
        except:
            pass
    def perform_fdr_correction(self):
        self.change_patterns = pd.concat([self.df_con, self.df_cat])
        self.change_patterns["is_changing"] = multitest.multipletests(self.change_patterns["P"], method="fdr_bh")[0]
        self.change_patterns["q"] = multitest.multipletests(self.change_patterns["P"], method="fdr_bh")[1]
        self.change_patterns_corrected = self.change_patterns.loc[self.change_patterns["is_changing"] == True]

    # Relationships

    def initialize_relationship_detection(self):
        self.rel_detector = RelationshipDetector(self.df_with_variants, self.case_id_column, self.activity_column, self.time_column, 
                                              self.attribute_list_con, self.attribute_list_cat, self.dfg, self.efg)
        self.df_con = pd.DataFrame()
        self.df_cat = pd.DataFrame()
    
    def prepare_correlation(self):
        self.rel_detector.prepare_correlation()
   
    def compute_correlation(self):
        self.rel_detector.compute_correlations()
        self.correlation_df = self.rel_detector.correlation_df
        cat_df = self.correlation_df.loc[self.correlation_df["method"] == "cramer"]
        cat_df = cat_df.loc[cat_df["scipy_corr"] > 0.25]
        self.correlation_df = self.rel_detector.correlation_df
        self.correlation_df = self.correlation_df.loc[(self.correlation_df["Act_1"] != self.correlation_df["Act_2"]) & 
                                                      (self.correlation_df["measure_1"] != self.correlation_df["measure_2"])]
        self.correlation_df["is_correlated"] = multitest.multipletests(self.correlation_df["P"], method="fdr_bh")[0]
        self.correlation_df["q"] = multitest.multipletests(self.correlation_df["P"], method="fdr_bh")[1]
        self.correlation_df_corrected = self.correlation_df.loc[self.correlation_df["is_correlated"] == True]
        self.correlation_df_corrected = pd.concat([self.correlation_df_corrected, cat_df])

    # Variant Comparison
    
    def initialize_variant_comparison(self, attribute, operator, value, var_name_1, var_name_2):
        self.var_comparator = VariantComparator(self.case_id_column, self.activity_column, self.time_column, attribute, operator, value, 
                                                self.df_with_variants, self.attribute_list_con, self.attribute_list_cat, self.dfg, var_name_1, var_name_2)
    
    def compute_variant_comparison(self):
        self.var_comparator.prepare()
        self.act_comparison_con = self.var_comparator.get_activity_comparison_results("con")
        self.act_comparison_cat = self.var_comparator.get_activity_comparison_results("cat")
        self.edge_comparison_con = self.var_comparator.get_edge_comparison_results("con")
        self.edge_comparison_cat = self.var_comparator.get_edge_comparison_results("cat")

    def perform_fdr_correction_comp_for_df(self, df: pd.DataFrame):
        df = df.loc[~df["p-val"].isna()]
        df["is_different"] = multitest.multipletests(df["p-val"], method="fdr_bh")[0]
        df["q"] = multitest.multipletests(df["p-val"], method="fdr_bh")[1]
        df = df.loc[df["is_different"] == True]
        return df

    def perform_fdr_correction_comp(self):
        self.act_comparison_con = self.perform_fdr_correction_comp_for_df(self.act_comparison_con)
        self.act_comparison_cat = self.perform_fdr_correction_comp_for_df(self.act_comparison_cat)
        self.edge_comparison_con = self.perform_fdr_correction_comp_for_df(self.edge_comparison_con)
        self.edge_comparison_cat = self.perform_fdr_correction_comp_for_df(self.edge_comparison_cat)