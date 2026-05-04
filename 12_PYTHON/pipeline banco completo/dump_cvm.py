import sys
sys.path.insert(0, '.')
from modules.coletor_cvm import ColetorCVM
from pathlib import Path

cvm = ColetorCVM(Path('cache'), usar_cache=True)
dados = cvm.baixar_dfp_multiplos_anos('906', [2024])
d2024 = dados.get(2024, {})

for doc, df in d2024.items():
    if df is None or (hasattr(df, 'empty') and df.empty):
        print(f'--- {doc}: VAZIO ---')
        continue
    print(f'\n=== {doc.upper()} ({len(df)} linhas) ===')
    if 'ORDEM_EXERC' in df.columns:
        df_ult = df[df['ORDEM_EXERC'].astype(str).str.contains('LTIMO|LAST|1', na=False)]
        if df_ult.empty:
            df_ult = df
    else:
        df_ult = df
    if 'CD_CONTA' in df_ult.columns and 'DS_CONTA' in df_ult.columns and 'VL_CONTA' in df_ult.columns:
        subset = df_ult[['CD_CONTA','DS_CONTA','VL_CONTA']].drop_duplicates('CD_CONTA')
        subset = subset[subset['VL_CONTA'].abs() > 0].sort_values('CD_CONTA')
        for _, row in subset.iterrows():
            cod = str(row['CD_CONTA']).ljust(20)
            val = f"{float(row['VL_CONTA']):>20,.0f}"
            desc = str(row['DS_CONTA'])[:70]
            print(f'  {cod}  {val}  {desc}')
    else:
        print(f'  Colunas: {list(df_ult.columns)}')
