import pandas as pd
import scipy


def prepare_dataframe_edges(variant, case_column, activity_column):
    # variant must be sorted by ['case:concept:name', 'time:timestamp']

    # joined = variant.join(variant.shift(-1).convert_dtypes(convert_string=False, convert_integer=False, convert_boolean=False, convert_floating=True), lsuffix='_l', rsuffix='_r')
    joined = variant.join(variant.shift(-1), lsuffix='_l', rsuffix='_r')
    joined = joined[joined[case_column + '_l'] == joined[case_column + '_r']]

    df_aggregated = joined.groupby([activity_column + '_l', activity_column + '_r']).agg(lambda x: x.tolist())
    #df_aggregated.drop([activity_column + '_l', activity_column + '_r'], axis=1, inplace=True)
    df_melted = pd.melt(df_aggregated.reset_index(), id_vars=[activity_column + '_l', activity_column + '_r'],
                        value_vars=df_aggregated.columns)
    df_final = df_melted[df_melted['value'].map(lambda d: len(d)) > 0]

    left_side_df = df_final[df_final['variable'].str.endswith('_l')]
    left_side_df['variable'] = left_side_df['variable'].apply(lambda row: row.rstrip('_l'))
    right_side_df = df_final[df_final['variable'].str.endswith('_r')]
    right_side_df['variable'] = right_side_df['variable'].apply(lambda row: row.rstrip('_r'))
    merged = left_side_df.merge(right_side_df, on=['variable', activity_column + '_l', activity_column + '_r'],
                                suffixes=['_l', '_r'])

    merged = merged[merged['value_l'] != merged['value_r']]
    return merged.set_index([activity_column + '_l', activity_column + '_r', 'variable'])


def prepare_dataframe_edges_categorical(variant, case_column, activity_column, continuous_columns, categorical_columns):
    variant = prepare_dataframe_edges(variant, case_column, activity_column)
    variant['value'] = variant.apply(
        lambda row: [str(row['value_l'][i]) + '-' + str(row['value_r'][i]) for i in range(0, len(row['value_l']))
                     if (not pd.isna(row['value_l'][i]) and not pd.isna(row['value_r'][i]))],
        axis=1)
    variant.drop(['value_l', 'value_r'], axis=1, inplace=True)
    return variant


def prepare_dataframe_edges_continuous(variant, case_column, activity_column, continuous_columns, categorical_columns):
    variant = prepare_dataframe_edges(variant, case_column, activity_column)
    variant['value'] = variant.apply(
        lambda row: [float(row['value_r'][i]) - float(row['value_l'][i]) for i in range(0, len(row['value_l']))
                     if (pd.api.types.is_numeric_dtype(type(row['value_l'][i])) and pd.api.types.is_numeric_dtype(type(row['value_r'][i])) and not pd.isna(row['value_l'][i]) and not pd.isna(row['value_r'][i]))],
        axis=1)
    variant.drop(['value_l', 'value_r'], axis=1, inplace=True)
    return variant


def prepare_dataframe_mean_per_activity_measurement(df, case_column, activity_column, continuous_columns, categorical_columns):
    cols = [case_column] + [activity_column] + continuous_columns
    df_meaned = df[cols]
    df_meaned = df_meaned.groupby([case_column, activity_column]).mean()
    return melt_prepared_dataframe(df_meaned, activity_column)


def prepare_dataframe_mode_per_activity_measurement(df, case_column, activity_column, continuous_columns, categorical_columns):
    cols = [case_column] + [activity_column] + categorical_columns
    df_moded = df[cols]
    df_moded = df_moded.groupby([case_column, activity_column]).agg(
        lambda x: scipy.stats.mode(x)[0])
    return melt_prepared_dataframe(df_moded, activity_column)


def melt_prepared_dataframe(df_prepared, activity_column):
    df_aggregated = df_prepared.groupby([activity_column]).agg(lambda x: x.dropna().tolist())
    df_melted = pd.melt(df_aggregated.reset_index(), id_vars=activity_column,
                        value_vars=df_aggregated.columns
                        )
    df_final = df_melted[df_melted['value'].map(lambda d: len(d)) > 0]
    return df_final.set_index([activity_column, 'variable'])


def join_prepared_dataframes(d1, d2, activity_column):
    return d1.join(d2, on=[activity_column, 'variable'], how='inner', lsuffix='_l', rsuffix='_r')


def join_prepared_dataframes_on_edges(d1, d2, activity_column):
    return d1.join(d2, on=[activity_column + '_l', activity_column + '_r', 'variable'], how='inner', lsuffix='_l', rsuffix='_r')
