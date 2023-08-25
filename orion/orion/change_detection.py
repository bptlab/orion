import numpy as np
import pandas as pd
import numpy as np
from scipy import stats
import pingouin as pg
from statsmodels.stats import multitest
from statsmodels.stats.contingency_tables import SquareTable as ST




class ChangeDetector:

    def __init__(self, df_with_variants: pd.DataFrame, case_id_column, activity_column, timestamp_column, attribute_list_con, attribute_list_cat, att_matrix, dfg, efg):
        self.df_with_variants = df_with_variants
        self.case_id_column = case_id_column
        self.activity_column = activity_column
        self.timestamp_column = timestamp_column
        self.dfg = dfg
        self.efg = efg
        self.attribute_list_con = attribute_list_con
        self.attribute_list_cat = attribute_list_cat
        self.att_matrix = att_matrix
        self.df_con = pd.DataFrame()
        self.df_cat = pd.DataFrame()
    
    
    def consecutive_hadms(self, df: pd.DataFrame, act_1, act_2):
        dfg_df = df.loc[((df[self.activity_column] == act_1) & (df["next_activity"] == act_2)) | ((df[self.activity_column] == act_2) & 
                                                                                                  (df["previous_activity"] == act_1))]                
        return dfg_df
    
    def eventually_follow_hadms(self, df: pd.DataFrame, act_1, act_2):
        df = df.loc[df[self.activity_column].isin([act_1, act_2])]
        df['previous_activity'] = df[self.activity_column].shift(periods=1)
        df['next_activity'] = df[self.activity_column].shift(periods=-1)
        a = df.drop_duplicates(self.case_id_column, keep="first").index.to_list()
        b = df.drop_duplicates(self.case_id_column, keep="last").index.to_list()
        df.loc[a, "previous_activity"] = np.nan
        df.loc[b, "next_activity"] = np.nan 
        efg_df = df.loc[((df[self.activity_column] == act_1) & (df["next_activity"] == act_2)) | ((df[self.activity_column] == act_2) & 
                                                                                                  (df["previous_activity"] == act_1))]                
        return efg_df
    
    #define methods for statistical tests
    def stat_value_con(self, act_1, act_2, ea, df: pd.DataFrame):
        f1 = df.loc[df[self.activity_column] == act_1][ea].to_frame().reset_index().drop("index", axis=1)
        f2 = df.loc[df[self.activity_column] == act_2][ea].to_frame().reset_index().drop("index", axis=1)
        df_wo_na = pd.concat([f1,f2], axis= 1)
        df_wo_na.columns = pd.RangeIndex(df_wo_na.columns.size)
        df_wo_na = df_wo_na.dropna()
        
        l1 = list(df_wo_na[0])
        l2 = list(df_wo_na[1])
        df1 = df_wo_na[0]
        df2 = df_wo_na[1]
        if((len(l1) < 8) | (len(l2) < 8)):
            return(np.nan,np.nan, np.nan, np.nan,np.nan,np.nan, np.nan, np.nan, np.nan, np.nan)
        try:
            if len(l1) > 30000:
                l1_1 = l1[0:30000]
                l2_2 = l2[0:30000]
            else:
                l1_1 = l1
                l2_2 = l2
            test = pg.wilcoxon(l1_1, l2_2)
            p = test["p-val"][0]
            cles = test["CLES"][0]
            rbc = test["RBC"][0]      
            return (p, cles, rbc, len(l1), df1.mean(), df2.mean(), df1.std(), df2.std(), l1_1, l2_2)
        except:
            return(1,0,0,0, 0, 0, 0, 0, 0, 0)
        

    def stat_value_cat(self, dep_1, dep_2, ea, df: pd.DataFrame):
        df_wo_na = df.loc[~df[ea].isna()]
        summary = df_wo_na.groupby(self.case_id_column).count()
        df_wo_na = summary.loc[summary[self.activity_column] == 2]
        hadms_wo_na = list(df_wo_na.reset_index()[self.case_id_column])
        df_wo_na = df.loc[df[self.case_id_column].isin(hadms_wo_na)]
        df = df_wo_na
        num_p = len(df.loc[(df[self.activity_column] == dep_1) & (~df[ea].isna())])
        count_1 = df.loc[(df[self.activity_column] == dep_1) & (~df[ea].isna())][ea].value_counts()
        val_1 = list(df.loc[(df[self.activity_column] == dep_1) & (~df[ea].isna())][ea])
        count_2 = df.loc[(df[self.activity_column] == dep_2) & (~df[ea].isna())][ea].value_counts()
        val_2 = list(df.loc[(df[self.activity_column] == dep_2) & (~df[ea].isna())][ea])
        if((len(count_1) < 2) | (len(count_2) < 2)):
            return(np.nan,np.nan, np.nan, np.nan, np.nan)
        g, p, chi2 = self.stuart_maxwell(df, ea)
        return (p, chi2, num_p, val_1, val_2)
    
    def stuart_maxwell(self, cons_df: pd.DataFrame, att):
        graph_stats = cons_df[[self.case_id_column, self.activity_column, att]]
        to_remove = graph_stats.loc[graph_stats[att].isna()][self.case_id_column]
        graph_stats = graph_stats.loc[~graph_stats[self.case_id_column].isin(to_remove)]
        curr_hadm = ""
        first_val = ""
        second_val = ""
        abnormal_col = graph_stats.columns[2]
        val_count = graph_stats[abnormal_col].value_counts()
        graph_cat = pd.DataFrame(columns=["Source", "Target", "Frequency"])
        for col_source in val_count.index:
            for col_target in val_count.index:
                new_row = {"Source":col_source, "Target":col_target, "Frequency": 0}
                graph_cat = pd.concat([graph_cat, pd.DataFrame([new_row])], ignore_index=True)
        for index, row in graph_stats.iterrows():
            if(curr_hadm != row[self.case_id_column]):
                curr_hadm = row[self.case_id_column]
                first_val = row[abnormal_col]
            else:
                second_val = row[abnormal_col]
                if((pd.isna(first_val)) | (pd.isna(second_val))):
                    pass
                else:
                    freq = graph_cat.loc[(graph_cat["Source"] == first_val) & (graph_cat["Target"] == second_val)]["Frequency"].iloc[0]
                    graph_cat.loc[(graph_cat["Source"] == first_val) & (graph_cat["Target"] == second_val), "Frequency"] = freq+1
        tab = graph_cat.set_index(['Source', 'Target'])
        tab = tab.unstack()
        tab.columns = tab.columns.get_level_values(1)
        sqtab = ST(tab)
        test = sqtab.homogeneity()
        p = test.pvalue
        chi2 = test.statistic
        return tab, p, chi2
    
    # perform statistical tests
    def detect_continuous_changes_in_dfg(self):
        #add next and previous activity for directly follows detection
        self.df_with_variants['previous_activity'] = self.df_with_variants[self.activity_column].shift(periods=1)

        self.df_with_variants['next_activity'] = self.df_with_variants[self.activity_column].shift(periods=-1)

        a = self.df_with_variants.drop_duplicates(self.case_id_column, keep="first").index.to_list()
        b = self.df_with_variants.drop_duplicates(self.case_id_column, keep="last").index.to_list()

        self.df_with_variants.loc[a, "previous_activity"] = np.nan
        self.df_with_variants.loc[b, "next_activity"] = np.nan

        for rel in self.dfg:
            att_list = self.att_matrix.loc[self.att_matrix[self.activity_column].isin([rel[0], rel[1]])].sum().to_frame().reset_index()
            att_list = att_list.rename({"index":"e_At", 0:"cardinality"}, axis=1)
            att_list = att_list.loc[(att_list["cardinality"] == 2) & (att_list["e_At"].isin(self.attribute_list_con))].reset_index()
            if len(att_list) != 0:
                consecutive_df = self.consecutive_hadms(self.df_with_variants, rel[0], rel[1])
                variants = consecutive_df["variant"].unique()
            for e_at in att_list["e_At"]:
                p, cles, rbc, num_p, m1, m2, st1, st2, l1, l2 = self.stat_value_con(rel[0], rel[1], e_at, consecutive_df)
                self.df_con = pd.concat([self.df_con, pd.DataFrame([{'Act_1': rel[0], 'Act_2': rel[1], 'E_At': e_at, 
                                                                    'P': p, "RBC": rbc, 'abs(RBC)': abs(rbc), 'var' : 'ALL', '#Samples' : num_p, 'M1':m1, 
                                                                    'M2':m2, 'ST1':st1, 'ST2':st2, 'Directly':True, 'Values_1':l1, 'Values_2':l2}])], ignore_index=True)    
                for var in variants:
                    df_var = consecutive_df.loc[consecutive_df["variant"] == var]
                    p, cles, rbc, num_p, m1, m2, st1, st2, l1, l2 = self.stat_value_con(rel[0], rel[1], e_at, df_var)
                    self.df_con = pd.concat([self.df_con, pd.DataFrame([{'Act_1': rel[0], 'Act_2': rel[1], 'E_At': e_at, 
                                                    'P': p, "RBC": rbc, 'abs(RBC)': abs(rbc), 'var' : var, '#Samples' : num_p, 'M1':m1, 
                                                    'M2':m2, 'ST1':st1, 'ST2':st2, 'Directly':True, 'Values_1':l1, 'Values_2':l2}])], ignore_index=True)  
    def detect_continuous_changes_in_efg(self):
        for rel in self.efg:
            att_list = self.att_matrix.loc[self.att_matrix[self.activity_column].isin([rel[0], rel[1]])].sum().to_frame().reset_index()
            att_list = att_list.rename({"index":"e_At", 0:"cardinality"}, axis=1)
            att_list = att_list.loc[(att_list["cardinality"] == 2) & (att_list["e_At"].isin(self.attribute_list_con))].reset_index()
            if len(att_list) != 0:
                consecutive_df = self.eventually_follow_hadms(self.df_with_variants, rel[0], rel[1])
                variants = consecutive_df["variant"].unique()
            for e_at in att_list["e_At"]:
                p, cles, rbc, num_p, m1, m2, st1, st2, l1, l2 = self.stat_value_con(rel[0], rel[1], e_at, consecutive_df)
                self.df_con = pd.concat([self.df_con, pd.DataFrame([{'Act_1': rel[0], 'Act_2': rel[1], 'E_At': e_at, 
                                                    'P': p, "RBC": rbc, 'abs(RBC)': abs(rbc), 'var' : 'ALL', '#Samples' : num_p, 'M1':m1, 
                                                    'M2':m2, 'ST1':st1, 'ST2':st2, 'Directly':False, 'Values_1':l1, 'Values_2':l2}])], ignore_index=True)   
                for var in variants:
                    df_var = consecutive_df.loc[consecutive_df["variant"] == var]
                    p, cles, rbc, num_p, m1, m2, st1, st2, l1, l2 = self.stat_value_con(rel[0], rel[1], e_at, df_var)
                    self.df_con = pd.concat([self.df_con, pd.DataFrame([{'Act_1': rel[0], 'Act_2': rel[1], 'E_At': e_at, 
                                                    'P': p, "RBC": rbc, 'abs(RBC)': abs(rbc), 'var' : var, '#Samples' : num_p, 'M1':m1, 
                                                    'M2':m2, 'ST1':st1, 'ST2':st2, 'Directly':False, 'Values_1':l1, 'Values_2':l2}])], ignore_index=True)  
    def detect_categorical_changes_in_dfg(self):
        self.df_with_variants['previous_activity'] = self.df_with_variants[self.activity_column].shift(periods=1)

        self.df_with_variants['next_activity'] = self.df_with_variants[self.activity_column].shift(periods=-1)

        a = self.df_with_variants.drop_duplicates(self.case_id_column, keep="first").index.to_list()
        b = self.df_with_variants.drop_duplicates(self.case_id_column, keep="last").index.to_list()

        self.df_with_variants.loc[a, "previous_activity"] = np.nan
        self.df_with_variants.loc[b, "next_activity"] = np.nan

        for rel in self.dfg:
            att_list = self.att_matrix.loc[self.att_matrix[self.activity_column].isin([rel[0], rel[1]])].sum().to_frame().reset_index()
            att_list = att_list.rename({"index":"e_At", 0:"cardinality"}, axis=1)
            att_list = att_list.loc[(att_list["cardinality"] == 2) & (att_list["e_At"].isin(self.attribute_list_cat))].reset_index()
            if len(att_list) != 0:
                consecutive_df = self.consecutive_hadms(self.df_with_variants, rel[0], rel[1])
                variants = consecutive_df["variant"].unique()
            for e_at in att_list["e_At"]:
                p, chi2, num_p, val_1, val_2 = self.stat_value_cat(rel[0], rel[1], e_at, consecutive_df)
                self.df_cat = pd.concat([self.df_cat, pd.DataFrame([{'Act_1': rel[0], 'Act_2': rel[1], 'E_At': e_at, 'P': p, 
                                                  "Chi2": chi2, 'var' : 'ALL', '#Samples' : num_p, 'Directly':True, 'Values_1':val_1, 'Values_2':val_2}])], ignore_index=True)
                for var in variants:
                    df_var = consecutive_df.loc[consecutive_df["variant"] == var]
                    p, chi2, num_p, val_1, val_2 = self.stat_value_cat(rel[0], rel[1], e_at, df_var)
                self.df_cat = pd.concat([self.df_cat, pd.DataFrame([{'Act_1': rel[0], 'Act_2': rel[1], 'E_At': e_at, 'P': p, 
                                                  "Chi2": chi2, 'var' : var, '#Samples' : num_p, 'Directly':True, 'Values_1':val_1, 'Values_2':val_2}])], ignore_index=True) 
    
    def detect_categorical_changes_in_efg(self):
        for rel in self.efg:
            #varianten aus consecutive df extrahieren
            att_list = self.att_matrix.loc[self.att_matrix[self.activity_column].isin([rel[0], rel[1]])].sum().to_frame().reset_index()
            att_list = att_list.rename({"index":"e_At", 0:"cardinality"}, axis=1)
            att_list = att_list.loc[(att_list["cardinality"] == 2) & (att_list["e_At"].isin(self.attribute_list_cat))].reset_index()
            if len(att_list) != 0:
                consecutive_df = self.eventually_follow_hadms(self.df_with_variants, rel[0], rel[1])
                variants = consecutive_df["variant"].unique()
            for e_at in att_list["e_At"]:
                p, chi2, num_p, val_1, val_2 = self.stat_value_cat(rel[0], rel[1], e_at, consecutive_df)
                self.df_cat = pd.concat([self.df_cat, pd.DataFrame([{'Act_1': rel[0], 'Act_2': rel[1], 'E_At': e_at, 'P': p, 
                                                  "Chi2": chi2, 'var' : 'ALL', '#Samples' : num_p, 'Directly':False, 'Values_1':val_1, 'Values_2':val_2}])], ignore_index=True)          
                for var in variants:
                    df_var = consecutive_df.loc[consecutive_df["variant"] == var]
                    p, chi2, num_p, val_1, val_2 = self.stat_value_cat(rel[0], rel[1], e_at, df_var)
                    self.df_cat = pd.concat([self.df_cat, pd.DataFrame([{'Act_1': rel[0], 'Act_2': rel[1], 'E_At': e_at, 'P': p, 
                                    "Chi2": chi2, 'var' : var, '#Samples' : num_p, 'Directly':False, 'Values_1':val_1, 'Values_2':val_2}])], ignore_index=True)