import pandas as pd
import numpy as np




class AttributeClassifier:

    def __init__(self, source_df: pd.DataFrame, case_id_column, activity_column, timestamp_column):
        self.df = source_df
        self.df = self.df.drop([timestamp_column], axis=1)
        self.case_id_column = case_id_column
        self.activity_column = activity_column
        self.timestamp_column = timestamp_column
        self.att_matrix = self.compute_attribute_matrix()
    
    def compute_attribute_matrix(self):
        att_matrix = pd.DataFrame(data=None,columns=self.df.columns)
        activities = self.df[self.activity_column].unique()
        n_Att = self.df.groupby(self.activity_column).agg({lambda x: x.notnull().sum()})
        n_Att.columns = n_Att.columns.droplevel(1)
        for act in activities:
            act_data = n_Att.loc[act]
            row = act_data.copy()
            for att in act_data.index:
                if act_data[att] > 0:
                    row[att] = 1
                else:
                    row[att] = 0
            row[self.activity_column] = act
            att_matrix = pd.concat([att_matrix, pd.DataFrame([row])], ignore_index=True)
        att_matrix = att_matrix.drop([self.case_id_column], axis=1)
        return att_matrix
    
    def compute_classification_scores_con_cat(self):
        #can be used for slider
        number_trace_occurence = self.df.groupby(self.case_id_column).agg({lambda x: x.notnull().sum()})
        number_trace_occurence.drop(self.activity_column, axis=1, inplace=True)
        number_trace_occurence.columns = number_trace_occurence.columns.droplevel(1)
        number_trace_occurence = number_trace_occurence.replace(0, np.NaN)
        number_trace_occurence = number_trace_occurence.mean()
        number_trace_occurence = number_trace_occurence.rename("numberOfTraceOccurence (Mean)")
        number_of_activities = pd.Series([], name="numberOfActivities")
        for col in self.df.columns:
            if((col != self.case_id_column) & (col != self.activity_column)):
                number_of_activities[col] = len(self.df[[self.activity_column, col]].dropna()[self.activity_column].unique())
        classification_scores_con_cat = pd.concat([number_of_activities, number_trace_occurence], axis=1)
        return classification_scores_con_cat
    
    def classifiy_con_cat(self, classification_scores_con_cat, con_cat_threshold):
        for col in self.df.columns:
            if (col != self.case_id_column) & (col != self.activity_column):
                if (self.df[col].nunique()/self.df[col].count() < con_cat_threshold):
                    classification_scores_con_cat.loc[col, "type"] = "categorical"
                else:
                    classification_scores_con_cat.loc[col, "type"] = "continuous"
    
    def classify_dynamic_attribute(self, classification_scores_con_cat):
        for index, row in classification_scores_con_cat.iterrows():
            if((row["numberOfActivities"] == 1) & (row["numberOfTraceOccurence (Mean)"] == 1)):
                classification_scores_con_cat.at[index, "class"] = "static"
            elif((row["numberOfActivities"] > 1) & (row["numberOfTraceOccurence (Mean)"] == 1)):
                classification_scores_con_cat.at[index, "class"] = "semi-dynamic"
            else:
                classification_scores_con_cat.at[index, "class"] = "dynamic"