import pandas as pd
import glob
import json
import os
import re

def find_column(columns, keywords):
    """Find a column that matches one of the keywords (case-insensitive)."""
    for col in columns:
        col_str = str(col).lower().strip()
        for kw in keywords:
            if kw.lower() in col_str:
                return col
    return None

def process_files():
    journal_data = {}
    
    # Look for both .xls and .xlsx files
    files = glob.glob('*.xls') + glob.glob('*.xlsx')
    
    print(f"Found {len(files)} files.")
    
    for file_path in files:
        file_name = os.path.basename(file_path)
        if file_name.startswith('~$') or file_name in ['process_data.py', 'inspect_excel.py']:
            continue
            
        journal_name = os.path.splitext(file_name)[0]
        print(f"Processing: {journal_name}")
        
        try:
            # Read Excel file
            # Try to read with default engine, if fails try specific engines
            try:
                df = pd.read_excel(file_path)
            except Exception as e:
                print(f"  Error reading {file_name}: {e}")
                continue

            # Identify columns
            cols = df.columns
            
            title_col = find_column(cols, ['Article Title', 'Title', '文章标题', '标题'])
            author_col = find_column(cols, ['Author Full Names', 'Authors', 'Author', '作者全名', '作者'])
            abstract_col = find_column(cols, ['Abstract', '摘要'])
            year_col = find_column(cols, ['Publication Year', 'Year', '发表年份', '年份'])
            
            if not all([title_col, author_col, abstract_col, year_col]):
                print(f"  Skipping {file_name}: Could not identify all required columns.")
                print(f"  Found: Title={title_col}, Author={author_col}, Abstract={abstract_col}, Year={year_col}")
                continue
                
            # Filter and Process
            journal_data[journal_name] = {}
            
            # Convert year to numeric, coerce errors to NaN
            df[year_col] = pd.to_numeric(df[year_col], errors='coerce')
            
            # Filter years 2015-2025
            df = df.dropna(subset=[year_col])
            df = df[(df[year_col] >= 2015) & (df[year_col] <= 2025)]
            
            # Sort by year descending
            df = df.sort_values(by=year_col, ascending=False)
            
            # Group by year
            for year, group in df.groupby(year_col):
                year_str = str(int(year))
                journal_data[journal_name][year_str] = []
                
                for _, row in group.iterrows():
                    article = {
                        'title': str(row[title_col]) if not pd.isna(row[title_col]) else '无标题',
                        'author': str(row[author_col]) if not pd.isna(row[author_col]) else '未知作者',
                        'abstract': str(row[abstract_col]) if not pd.isna(row[abstract_col]) else '无摘要'
                    }
                    journal_data[journal_name][year_str].append(article)
            
            print(f"  Loaded {len(df)} articles.")
            
        except Exception as e:
            print(f"  Error processing {file_name}: {e}")

    # Write to data.js
    with open('data.js', 'w', encoding='utf-8') as f:
        json_str = json.dumps(journal_data, ensure_ascii=False, indent=2)
        f.write(f"const journalData = {json_str};")
    
    print("Done! generated data.js")

if __name__ == "__main__":
    process_files()
