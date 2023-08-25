import pm4py
from pm4py.algo.filtering.log.variants import variants_filter
from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
from pm4py.statistics.eventually_follows.log import get as efg_get
import pandas as pd




class LogPreprocessor:

    def __init__(self, source_df: pd.DataFrame, case_id_column, activity_column, timestamp_column):
        self.source_df = source_df
        self.case_id_column = case_id_column
        self.activity_column = activity_column
        self.timestamp_column = timestamp_column
        
        self.source_df[self.timestamp_column] = self.source_df[self.timestamp_column].apply(lambda x: pd.to_datetime(x))
        log = pm4py.format_dataframe(self.source_df.copy(), case_id=self.case_id_column, activity_key=self.activity_column, 
                                                timestamp_key=self.timestamp_column)
        self.event_log = pm4py.convert_to_event_log(log)
        self.dfg = dfg_discovery.apply(self.event_log)
        self.efg = efg_get.apply(self.event_log)
        # call context-aware methods
        self.activity_count = pm4py.get_event_attribute_values(self.event_log, "concept:name")
        self.activities = []
        for activity in self.activity_count: self.activities.append(activity)
        self.dfr_matrix = pd.DataFrame(columns=self.activities, index=self.activities)
        self.dpr_matrix = pd.DataFrame(columns=self.activities, index=self.activities)
        self.fill_dfr_dpr_matrix()
        self.repetition_scores = pd.DataFrame(columns=["repetition_score"], index=self.activities)
        self.calc_repetition_score()
        self.recurring_activities = []


    def add_variants(self):
        variants = variants_filter.get_variants(self.event_log)
        variants = list(variants.keys())
        var = self.source_df.groupby(self.case_id_column)[self.activity_column].apply(list).reset_index()
        var[self.activity_column] = var[self.activity_column].apply(lambda x: ','.join(map(str, x)))
        var = var.rename({self.activity_column:"variant"}, axis=1)
        return self.source_df.merge(var, how="left", on=self.case_id_column)
    
    # context-aware methods
    def fill_dfr_dpr_matrix(self):
        for act_1 in self.activity_count:
            for act_2 in self.activity_count:  
                dfr_total = self.dfg[(act_1, act_2)]
                dpr_total = self.dfg[(act_2, act_1)]
                act_count = self.activity_count[act_2]
                dfr_res = dfr_total/act_count
                dpr_res = dpr_total/act_count
                self.dfr_matrix.loc[act_1, act_2] = dfr_res
                self.dpr_matrix.loc[act_1, act_2] = dpr_res
    
    def calc_repetition_score(self):
        for act in self.activities:
            act_dfr = list(self.dfr_matrix.loc[act])
            act_dpr = list(self.dpr_matrix.loc[act])
            self.repetition_scores.loc[act, "repetition_score"] = (sum(act_dfr) + sum(act_dpr)) / ((len(self.activities)+1) * 2)

    def identify_context(self, lambd, ignore_activities: list):
        self.mapping_before = {}
        self.mapping_after = {}
        for val in self.recurring_activities:
            names_before = list(self.dfr_matrix.loc[val].index)
            names_after = list(self.dpr_matrix.loc[val].index)
            self.mapping_before[val] = []
            self.mapping_after[val] = []
            for index,rep_score in enumerate(self.dfr_matrix.loc[val]):
                if names_before[index] in self.recurring_activities or names_before[index] in ignore_activities:
                    continue
                if rep_score > lambd:
                    self.mapping_before[val].append(names_before[index])
            for index,rep_score in enumerate(self.dpr_matrix.loc[val]):
                if names_after[index] in self.recurring_activities or names_after[index] in ignore_activities:
                    continue
                if rep_score > lambd:
                    self.mapping_after[val].append(names_after[index])


    def transform_event(self, df, rep_event, rep_mapping_before, rep_mapping_after):
        #refactor with loc function as in directly follows extraction
        rows_to_add_intern = []
        row_to_add = {}
        case_ids = list(df[self.case_id_column].unique())
        for case_id in case_ids:
            df_case = df.loc[df[self.case_id_column] == case_id]
            for index, row in df_case.iterrows():
                if row[self.activity_column] == rep_event:
                    try:
                        if df_case.loc[index+1][self.activity_column] in rep_mapping_before:
                            row_to_add = row
                            row_to_add[self.activity_column] = row_to_add[self.activity_column] + " BEFORE " + df_case.loc[index+1][self.activity_column]
                            row_to_add["event_time"] = df_case.loc[index+1][self.timestamp_column]
                            row_to_add["time_diff"] = row_to_add["event_time"] - row_to_add[self.timestamp_column]
                            rows_to_add_intern.append(row_to_add)
                    except:
                        pass
            for index, row in df_case.iterrows():
                if row[self.activity_column] == rep_event:
                    try:
                        if df_case.loc[index-1][self.activity_column] in rep_mapping_after:
                            row_to_add = row
                            row_to_add[self.activity_column] = row_to_add[self.activity_column] + " AFTER " + df_case.loc[index-1][self.activity_column]
                            row_to_add["event_time"] = df_case.loc[index-1][self.timestamp_column]
                            row_to_add["time_diff"] = row_to_add[self.timestamp_column] - row_to_add["event_time"]
                            rows_to_add_intern.append(row_to_add)
                    except:
                        pass
        rows_to_add_intern = pd.DataFrame(rows_to_add_intern)
        rows_to_add_intern = rows_to_add_intern.sort_values([self.timestamp_column, "time_diff"])
        rows_to_add_intern = rows_to_add_intern.drop_duplicates([self.case_id_column, self.timestamp_column], keep="first")
        return rows_to_add_intern
    
    def transform_event_log(self):
        df_new_rows = pd.DataFrame()
        for rep_event in self.recurring_activities:
            if (len(self.mapping_before[rep_event]) != 0) or (len(self.mapping_after[rep_event]) != 0):
                df_e = self.source_df.copy()
                for e in self.recurring_activities:
                    if e != rep_event:
                        df_e = df_e.loc[df_e[self.activity_column] != e]
                df_e = df_e.sort_values([self.case_id_column, self.timestamp_column])
                df_e = df_e.reset_index().drop("index", axis=1)
                rows_to_add = self.transform_event(df_e, rep_event, self.mapping_before[rep_event], self.mapping_after[rep_event])
                df_new_rows = pd.concat([df_new_rows, rows_to_add])
        new_df = self.source_df.copy()
        for rep_event in self.recurring_activities:
            new_df = new_df.loc[new_df[self.activity_column] != rep_event]
        new_df = pd.concat([new_df, df_new_rows])
        new_df = new_df.sort_values([self.case_id_column, self.timestamp_column])
        try:
            new_df.drop(["event_time", "time_diff"], axis=1, inplace=True)
        except:
            pass
        self.source_df = new_df
        log = pm4py.format_dataframe(self.source_df.copy(), case_id=self.case_id_column, activity_key=self.activity_column, 
                                                timestamp_key=self.timestamp_column)
        self.event_log = pm4py.convert_to_event_log(log)
        self.dfg = dfg_discovery.apply(self.event_log)
        self.efg = efg_get.apply(self.event_log)
        