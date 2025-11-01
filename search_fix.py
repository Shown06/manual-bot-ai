def enhanced_search_content(self, query, manual, max_sections=8):
    if not manual.strip():
        return ""
    
    # 改行で分割（日本語対応）
    lines = manual.split('\n')
    scored_lines = []
    query_lower = query.lower()
    
    # 日本語の単語分割を改善
    import re
    query_words = re.findall(r'[a-zA-Z]+|[ぁ-んァ-ヶー一-龥]+|\d+', query)
    
    for i, line in enumerate(lines):
        if len(line.strip()) < 5:
            continue
        
        line_lower = line.lower()
        score = 0
        
        # キーワードマッチング
        for word in query_words:
            if word.lower() in line_lower:
                score += 3
        
        # 部分一致も評価
        if query_lower in line_lower:
            score += 5
        
        # 前後の文脈も含める
        context = ""
        if i > 0:
            context += lines[i-1] + " "
        context += line
        if i < len(lines) - 1:
            context += " " + lines[i+1]
            
        if score > 0:
            scored_lines.append((context, score))
    
    scored_lines.sort(key=lambda x: x[1], reverse=True)
    return "\n".join([line for line, score in scored_lines[:max_sections]])
