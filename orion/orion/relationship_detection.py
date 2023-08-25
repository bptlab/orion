import pandas as pd
import numpy as np
import scipy
from scipy import stats
from scipy.stats import shapiro


class RelationshipDetector:
        
    def __init__(self, df_with_variants: pd.DataFrame, case_id_column, activity_column, timestamp_column, attribute_list_con, attribute_list_cat, dfg, efg):
        self.df_with_variants = df_with_variants
        self.case_id_column = case_id_column
        self.activity_column = activity_column
        self.timestamp_column = timestamp_column
        self.dfg = dfg
        self.efg = efg
        self.continuous_columns = attribute_list_con  + [self.timestamp_column]
        self.categorical_columns = attribute_list_cat

    def prepare_correlation(self):
        self.prepare_continuous_correlation()
        self.prepare_categorical_correlation()
        self.prepare_con_cat_correlation()


    #correlation preparation
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

    def prepare_continuous_correlation(self):
        #extra function for efg --> efg - dfg --> apply function --> store and make similar df to outcome of this function
        # for continuous columns
        continuous_diff_df = self.df_with_variants.set_index([self.case_id_column, self.activity_column])[self.continuous_columns].diff().reset_index()
        continuous_diff_df['previous_activity'] = continuous_diff_df[self.activity_column].shift(periods=1)
        continuous_diff_df = continuous_diff_df.groupby(self.case_id_column).apply(lambda group: group.iloc[1:])

        # add time perspective
        continuous_diff_df['duration'] = continuous_diff_df[self.timestamp_column].dt.seconds
        continuous_diff_df['sum_timestamp'] = continuous_diff_df['duration'].rolling(2).sum()
        continuous_diff_df.drop(['duration', self.timestamp_column], axis=1, inplace=True)

        self.continuous_diff_df = continuous_diff_df
        continuous_grouped_df = self.continuous_diff_df.groupby([self.activity_column, 'previous_activity']).agg(list)
        continuous_grouped_df["Directly"] = True
        self.continuous_grouped_df = continuous_grouped_df
        
        for rel in self.efg:
            act_1 = rel[0]
            act_2 = rel[1]
            df_efg = self.eventually_follow_hadms(self.df_with_variants, act_1, act_2)
            df_efg = df_efg.set_index([self.case_id_column, self.activity_column])[self.continuous_columns].diff().reset_index()
            df_efg['previous_activity'] = df_efg[self.activity_column].shift(periods=1)
            df_efg = df_efg.groupby(self.case_id_column).apply(lambda group: group.iloc[1:])
            #add time
            df_efg['sum_timestamp'] = df_efg[self.timestamp_column].dt.seconds
            df_efg_grouped = df_efg.groupby([self.activity_column, 'previous_activity']).agg(list)
            df_efg_grouped["Directly"] = False
            self.continuous_grouped_df = pd.concat([self.continuous_grouped_df, df_efg_grouped])

        self.continuous_grouped_df = self.continuous_grouped_df.sort_index()

    def prepare_categorical_correlation(self):
        diff_df = self.df_with_variants.set_index([self.case_id_column, self.activity_column])[self.categorical_columns].reset_index()
        shifted_df = diff_df.shift(periods = 1)
        joined_df = diff_df.join(shifted_df, rsuffix='_prev')
        joined_df = joined_df.groupby(self.case_id_column).apply(lambda group: group.iloc[1:])

        change_list = []
        for i, row in joined_df.iterrows():
            list_item = {
                self.case_id_column: row[self.case_id_column],
                'previous_activity': row[self.activity_column + '_prev'],
                self.activity_column: row[self.activity_column]
            }
            for col in self.categorical_columns:
                list_item[col] = f"{row[col + '_prev']}-{row[col]}"
            change_list.append(list_item)
        change_df = pd.DataFrame(change_list)
        self.prepared_categorical_df = change_df.groupby(['previous_activity', self.activity_column]).agg(list)
        self.prepared_categorical_df["Directly"] = True

        for rel in self.efg:
            act_1 = rel[0]
            act_2 = rel[1]
            df_efg = self.eventually_follow_hadms(self.df_with_variants, act_1, act_2)
            df_efg = df_efg.set_index([self.case_id_column, self.activity_column])[self.categorical_columns].reset_index()
            shifted_df = df_efg.shift(periods = 1)
            joined_df = df_efg.join(shifted_df, rsuffix='_prev')
            joined_df = joined_df.groupby(self.case_id_column).apply(lambda group: group.iloc[1:])
            change_list = []
            for i, row in joined_df.iterrows():
                list_item = {
                    self.case_id_column: row[self.case_id_column],
                    'previous_activity': row[self.activity_column + '_prev'],
                    self.activity_column: row[self.activity_column]
                }
                for col in self.categorical_columns:
                    list_item[col] = f"{row[col + '_prev']}-{row[col]}"
                change_list.append(list_item)
            change_df = pd.DataFrame(change_list)
            cat_grouped = change_df.groupby(['previous_activity', self.activity_column]).agg(list)
            cat_grouped["Directly"] = False
            self.prepared_categorical_df = pd.concat([self.prepared_categorical_df, cat_grouped])
        self.prepared_categorical_df = self.prepared_categorical_df.sort_index()

    def prepare_con_cat_correlation(self):
        self.continuous_grouped_df = self.continuous_grouped_df.reset_index()
        self.continuous_grouped_df = self.continuous_grouped_df.set_index(["previous_activity", self.activity_column, "Directly"])
        self.prepared_categorical_df = self.prepared_categorical_df.reset_index()
        self.prepared_categorical_df = self.prepared_categorical_df.set_index(["previous_activity", self.activity_column, "Directly"])
        con_grouped = self.continuous_grouped_df
        cat_grouped = self.prepared_categorical_df
        #con_grouped = con_grouped.reorder_levels(['previous_activity', self.activity_column]).sort_index()
        con_cat = con_grouped.merge(cat_grouped, left_index=True, right_on=["previous_activity", self.activity_column, "Directly"], how="left")
        con_cat.drop(self.case_id_column + '_y', axis=1, inplace=True)
        con_cat.rename(columns={self.case_id_column + '_x':self.case_id_column}, inplace=True)
        self.con_cat = con_cat


    #correlation computation

    def compute_correlations(self):
        self.compute_correlations_continuous()
        print("#########################FINISHED CON#################")
        self.compute_correlations_categorical()
        print("#########################FINISHED CAT#################")
        self.compute_correlations_con_cat()
        self._merge_correlation_dfs()

    def compute_correlations_continuous(self):

        # correlate all values for each row
        #i, j columns of row to correlate
        temp_row  = self.continuous_grouped_df.reset_index().iloc[1]
        pearson = []
        spearman = []
        columns_not_to_correlate = [self.timestamp_column, 'previous_activity', self.activity_column, self.case_id_column, "Directly"]
        for index, temp_row in self.continuous_grouped_df.reset_index().iterrows():
            for i in range(len(temp_row.index)):
                for j in range(i, len(temp_row.index)):
                    try:
                        if temp_row.index[i] not in columns_not_to_correlate and temp_row.index[j] not in columns_not_to_correlate:
                            # remove measurements w/o values for this transition
                            if ~np.isnan(temp_row[i]).all() and ~np.isnan(temp_row[j]).all():
                                usable_indices = np.intersect1d(np.where(~np.isnan(temp_row[i]))[0], np.where(~np.isnan(temp_row[j]))[0])
                                # scipy.pearsonr only works with 2 or more samples
                                if len(usable_indices) > 2:
                                    # check whether or not both data pairs are normal distributed                                      
                                    scipy_coef = scipy.stats.spearmanr(np.array(temp_row[i])[usable_indices], np.array(temp_row[j])[usable_indices])
                                    spearman.append([temp_row['previous_activity'], temp_row[self.activity_column], temp_row.index[i], temp_row.index[j], len(usable_indices), scipy_coef[0], scipy_coef[1], np.array(temp_row[i])[usable_indices], np.array(temp_row[j])[usable_indices], temp_row["Directly"]])
                    except Exception as e:
                        print(e)
                                
        self.spearman_df = pd.DataFrame(spearman, columns = ['Act_1', 'Act_2', 'measure_1', 'measure_2', 'sample_size', 'scipy_corr', 'P', 'values_1', 'values_2', 'Directly'])
        
    def compute_correlations_categorical(self):
        # correlate all values for each row
        craemers_v = []
        for index, temp_row in self.prepared_categorical_df.reset_index().iterrows():
            for i in range(len(temp_row.index)):
                for j in range(i+1, len(temp_row.index)):
                    try:
                        if temp_row.index[i] not in ['previous_activity', self.activity_column, self.case_id_column, "Directly"] and temp_row.index[j] not in ['previous_activity', self.activity_column, self.case_id_column, "Directly"]:
                            # remove measurements w/o values for this transition
                            if ~(np.array(temp_row[i]) == 'nan-nan').all() and ~(np.array(temp_row[j]) == 'nan-nan').all():
                                usable_indices = np.intersect1d(
                                    np.flatnonzero(np.core.defchararray.find(temp_row[i],'nan')<0),                             
                                    np.flatnonzero(np.core.defchararray.find(temp_row[j],'nan')<0)
                                )
                                if len(usable_indices) >= 2:
                                    coef = self.cramer_v(np.array(temp_row[i])[usable_indices], np.array(temp_row[j])[usable_indices])
                                    craemers_v.append([temp_row['previous_activity'], temp_row[self.activity_column], temp_row.index[i], temp_row.index[j], len(usable_indices), coef, np.array(temp_row[i])[usable_indices], np.array(temp_row[j])[usable_indices], temp_row["Directly"]])
                    except Exception as e:
                        print(e)
        self.cramer_df = pd.DataFrame(craemers_v, columns = ['Act_1', 'Act_2', 'measure_1', 'measure_2', 'sample_size', 'scipy_corr', 'values_1', 'values_2', 'Directly'])
    
                
    def compute_correlations_con_cat(self):
        con_columns = self.continuous_columns.copy()
        con_columns.remove(self.timestamp_column)
        con_columns.append("sum_timestamp")
        cat_columns = self.categorical_columns.copy()
        con_cat = self.con_cat
        anova = []
        kruskal = []
        for index, temp_row in con_cat.reset_index().iterrows():
            for con in con_columns:
                for cat in cat_columns:
                    try:
                    # remove measurements w/o values for this transition
                        if ~np.isnan(temp_row[con]).all() and ~(np.array(temp_row[cat]) == 'nan-nan').all():
                            usable_indices = np.intersect1d(
                                np.where(~np.isnan(temp_row[con]))[0],                             
                                np.flatnonzero(np.core.defchararray.find(temp_row[cat],'nan')<0)
                            )
                            if len(usable_indices) >= 2:
                                cat_dict = {}
                                cat_usable = np.array(temp_row[cat])[usable_indices]
                                unique_cats = np.unique(cat_usable)
                                #get values for each category
                                for unique_cat in unique_cats:
                                    cat_index = np.where(np.array(temp_row[cat]) == unique_cat)[0]
                                    cat_usable_index = np.intersect1d(cat_index, usable_indices)
                                    con_unique_cat = np.array(temp_row[con])[cat_usable_index]
                                    cat_dict[unique_cat] = con_unique_cat
                                if len(cat_dict) > 1:        
                                    kruskal_test = stats.kruskal(*(cat_dict[v] for v in cat_dict))
                                    kruskal.append([temp_row['previous_activity'], temp_row[self.activity_column], con, cat, len(usable_indices), kruskal_test[0], kruskal_test[1], cat_usable, np.array(temp_row[con])[usable_indices], temp_row["Directly"]])
                    except Exception as e:
                            print(e)
        self.kruskal_df = pd.DataFrame(kruskal, columns = ['Act_1', 'Act_2', 'measure_1', 'measure_2', 'sample_size', 'stat', 'P', 'values_1', 'values_2', 'Directly'])
    

    def compute_correlation_of_one_with_all_cells(self, act_1, act_2, measure, var_1):
        con_columns = self.continuous_columns.copy()
        con_columns.remove(self.timestamp_column)
        con_columns.append("sum_timestamp")
        cat_columns = self.categorical_columns.copy()
        con_cat = self.con_cat
        corr_arr = []
        for index, temp_row in con_cat.reset_index().iterrows():
            act_3 = temp_row['previous_activity']
            act_4 = temp_row[self.activity_column]
            if act_3 == act_1 and act_4 == act_2:
                pass
            else:
                for col in con_cat.columns:
                    if col != self.case_id_column and col != self.time_column:
                        corr, p, s, sample_size, method, method_2, val_1, val_2 = self.compute_correlation_for_single_cell(act_1, act_2, act_3, act_4, measure, col, "", "")
                        corr_arr.append([act_1, act_2, act_3, act_4, measure, col, sample_size, corr, p, s, method, method_2, val_1, val_2])
        corr_df = pd.DataFrame(corr_arr, columns=['Act_1', 'Act_2', 'Act_3', 'Act_4',  'measure_1', 'measure_2', 'sample_size', 'scipy_corr', 'P', 'stat', 'method', 'method_2', 'values_1', 'values_2'])
        corr_df = corr_df.loc[corr_df["sample_size"] > 0].reset_index().drop("index", axis=1)
        return corr_df
                

    
    def compute_correlation_for_single_cell(self, act_1, act_2, act_3, act_4, eA_1, eA_2, var_1, var_2):
        
        con_columns = self.continuous_columns.copy()
        con_columns.remove(self.timestamp_column)
        con_columns.append("sum_timestamp")
        cat_columns = self.categorical_columns.copy()
        con_cat = self.con_cat
        
        #Get data types of event attributes
        first_ea_type = ""
        second_ea_type = ""
        
        if eA_1 in con_columns:
            first_ea_type = "con"
        else:
            first_ea_type = "cat"


        if eA_2 in con_columns:
            second_ea_type = "con"
        else:
            second_ea_type = "cat"
        
        row_rel_1 = con_cat.loc[(act_1, act_2)]
        row_rel_2 = con_cat.loc[(act_3, act_4)]
        if not isinstance(row_rel_1, pd.Series):
            row_rel_1 = con_cat.loc[(act_1, act_2)].iloc[0]
        if not isinstance(row_rel_2, pd.Series):  
            row_rel_2 = con_cat.loc[(act_3, act_4)].iloc[0]
        usable_case_ids = np.intersect1d(row_rel_1[self.case_id_column], row_rel_2[self.case_id_column])
        usable_case_ids_1 = np.isin(row_rel_1[self.case_id_column], usable_case_ids)
        usable_case_ids_2 = np.isin(row_rel_2[self.case_id_column], usable_case_ids)
        usable_case_index_1 = np.where(usable_case_ids_1 == True)[0]
        usable_case_index_2 = np.where(usable_case_ids_2 == True)[0]
        usable_values_1 = np.array(row_rel_1[eA_1])[usable_case_index_1]
        usable_values_2 = np.array(row_rel_2[eA_2])[usable_case_index_2]

        #two functions - one for usable indices, one for statistical tests and cat preprocessing
        if len(usable_values_1) > 0 and len(usable_values_2) > 0:
            usable_indices = self.retrieve_usable_indices(first_ea_type, second_ea_type, usable_values_1, usable_values_2)
        else:
            return (0, 1, 0, 0, "", "", 0, 0)
        if len(usable_indices) <= 2:
            return (0, 1, 0, 0, "", "", 0, 0)
        else:
            corr, p, s, method, method_2 = self.calculate_correlation(first_ea_type, second_ea_type, usable_values_1, usable_values_2, usable_indices, act_1, act_2, act_3, act_4, eA_1, eA_2)
        return corr, p, s, len(usable_indices), method, method_2, np.array(usable_values_1)[usable_indices], np.array(usable_values_2)[usable_indices]

    def calculate_correlation(self, first_ea_type, second_ea_type, usable_values_1, usable_values_2, usable_indices, act_1, act_2, act_3, act_4, eA_1, eA_2):
        p = 1
        s = 0
        corr = 0
        method = ""
        method_2 = ""

        if first_ea_type == "con" and second_ea_type == "con":
            if ~np.isnan(usable_values_1).all() and ~np.isnan(usable_values_2).all():
                scipy_coef = scipy.stats.spearmanr(np.array(usable_values_1)[usable_indices], np.array(usable_values_2)[usable_indices])
                corr = scipy_coef[0]
                method = 'spearman'
                if eA_1 == eA_2 and (act_1 != act_3 and act_2 != act_4):
                    wilcoxon = pg.wilcoxon(np.array(usable_values_1)[usable_indices], np.array(usable_values_2)[usable_indices])
                    method_2 = "wilcoxon"
                    p = wilcoxon["p-val"][0]
                    s = wilcoxon["RBC"][0]
        elif first_ea_type == "con" and second_ea_type == "cat":
            if ~np.isnan(usable_values_1).all() and ~(np.array(usable_values_2) == 'nan-nan').all():
                cat_dict = {}
                cat_usable = np.array(usable_values_2)[usable_indices]
                unique_cats = np.unique(cat_usable)
                #get values for each category
                for unique_cat in unique_cats:
                    cat_index = np.where(np.array(usable_values_2) == unique_cat)[0]
                    cat_usable_index = np.intersect1d(cat_index, usable_indices)
                    con_unique_cat = np.array(usable_values_1)[cat_usable_index]
                    cat_dict[unique_cat] = con_unique_cat
                if len(cat_dict) > 1:
                    #perform kruskal-wallis test        
                    kruskal_test = stats.kruskal(*(cat_dict[v] for v in cat_dict))
                    p = kruskal_test[1]
                    s = kruskal_test[0]
                    method = 'kruskal'
        elif first_ea_type == "cat" and second_ea_type == "con":
            if ~np.isnan(usable_values_2).all() and ~(np.array(usable_values_1) == 'nan-nan').all():
                cat_dict = {}
                cat_usable = np.array(usable_values_1)[usable_indices]
                unique_cats = np.unique(cat_usable)
                #get values for each category
                for unique_cat in unique_cats:
                    cat_index = np.where(np.array(usable_values_1) == unique_cat)[0]
                    cat_usable_index = np.intersect1d(cat_index, usable_indices)
                    con_unique_cat = np.array(usable_values_2)[cat_usable_index]
                    cat_dict[unique_cat] = con_unique_cat
                if len(cat_dict) > 1:
                    #perform kruskal-wallis test        
                    kruskal_test = stats.kruskal(*(cat_dict[v] for v in cat_dict))
                    p = kruskal_test[1]
                    s = kruskal_test[0]
                    method = 'kruskal'
        elif first_ea_type == "cat" and second_ea_type == "cat":
            if ~(np.array(usable_values_1) == 'nan-nan').all() and ~(np.array(usable_values_2) == 'nan-nan').all():
                corr = self.cramer_v(np.array(usable_values_1)[usable_indices], np.array(usable_values_2)[usable_indices])
                method = 'cramer'
        return corr, p, s, method, method_2
    
    #helper functions

    def retrieve_usable_indices(self, first_ea_type, second_ea_type, usable_values_1, usable_values_2):
        usable_indices = []
        if first_ea_type == "con" and second_ea_type == "con":
            if ~np.isnan(usable_values_1).all() and ~np.isnan(usable_values_2).all(): 
                usable_indices = np.intersect1d(np.where(~np.isnan(usable_values_1))[0], np.where(~np.isnan(usable_values_2))[0])
        elif first_ea_type == "con" and second_ea_type == "cat":
            if ~np.isnan(usable_values_1).all() and ~(np.array(usable_values_2) == 'nan-nan').all():
                usable_indices = np.intersect1d(
                    np.where(~np.isnan(usable_values_1))[0],                             
                    np.flatnonzero(np.core.defchararray.find(usable_values_2,'nan')<0))
        elif first_ea_type == "cat" and second_ea_type == "con":
            if ~np.isnan(usable_values_2).all() and ~(np.array(usable_values_1) == 'nan-nan').all():
                usable_indices = np.intersect1d(
                    np.where(~np.isnan(usable_values_2))[0],                             
                    np.flatnonzero(np.core.defchararray.find(usable_values_1,'nan')<0))
        elif first_ea_type == "cat" and second_ea_type == "cat":
            if ~(np.array(usable_values_1) == 'nan-nan').all() and ~(np.array(usable_values_2) == 'nan-nan').all():
                usable_indices = np.intersect1d(
                    np.flatnonzero(np.core.defchararray.find(usable_values_1,'nan')<0),                             
                    np.flatnonzero(np.core.defchararray.find(usable_values_2,'nan')<0))
        return usable_indices
    
    def _merge_correlation_dfs(self):
        ## merge pearson and spearson df
        self.spearman_df = self.spearman_df.dropna()
        self.cramer_df  = self.cramer_df.dropna()
        self.spearman_df['method'] = 'spearman'
        self.cramer_df['method'] = 'cramer'
        self.kruskal_df['method'] = 'kruskal'
        self.correlation_df = pd.concat([self.spearman_df, self.cramer_df, self.kruskal_df])
        self.correlation_df = self.correlation_df[["Act_1", "Act_2", "measure_1", "measure_2", "sample_size", "scipy_corr", "P", "stat", "method", "values_1", "values_2", "Directly"]]
        self.continuous_correlation_df = self.spearman_df

    def cramer_v(self, values_1, values_2):
        # generate contingency table
        (val_1, val_2), count = stats.contingency.crosstab(values_1, values_2)
        # Finding Chi-squared test statistic, 
        # sample size, and minimum of rows and
        # columns
        X2 = stats.chi2_contingency(count, correction=False)[0]
        N = np.sum(count)
        minimum_dimension = min(count.shape)-1

        # Calculate Cramer's V
        return(np.sqrt((X2/N) / minimum_dimension))