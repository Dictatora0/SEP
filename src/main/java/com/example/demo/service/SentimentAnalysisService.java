package com.example.demo.service;

import com.hankcs.hanlp.HanLP;
import com.hankcs.hanlp.seg.common.Term;
import org.springframework.stereotype.Service;
import java.util.*;

@Service
public class SentimentAnalysisService {
    
    // 积极词典
    private static final Set<String> POSITIVE_WORDS = new HashSet<>(Arrays.asList(
        "好", "棒", "赞", "优秀", "满意", "喜欢", "推荐", "不错", "完美", "超值",
        "好用", "漂亮", "实惠", "划算", "给力", "惊喜", "舒适", "方便", "实用",
        "精美", "高端", "大气", "上档次", "物美价廉", "物超所值", "性价比高",
        "质量好", "做工好", "包装好", "服务好", "态度好", "速度快", "发货快",
        "物流快", "正品", "真品", "新品", "全新", "完好", "完整", "齐全"
    ));

    // 消极词典
    private static final Set<String> NEGATIVE_WORDS = new HashSet<>(Arrays.asList(
        "差", "烂", "糟", "失望", "后悔", "不推荐", "不行", "不好", "差劲", "垃圾",
        "贵", "贵了", "不值", "浪费", "退货", "退款", "投诉", "问题", "故障",
        "损坏", "瑕疵", "缺陷", "不足", "不满意", "不划算", "不实用",
        "质量差", "做工差", "包装差", "服务差", "态度差", "速度慢", "发货慢",
        "物流慢", "假货", "仿品", "二手", "旧", "破损", "残缺", "不齐"
    ));

    // 程度副词及其权重
    private static final Map<String, Double> DEGREE_WORDS = new HashMap<>();
    static {
        DEGREE_WORDS.put("非常", 1.5);
        DEGREE_WORDS.put("很", 1.3);
        DEGREE_WORDS.put("太", 1.3);
        DEGREE_WORDS.put("特别", 1.2);
        DEGREE_WORDS.put("比较", 0.8);
        DEGREE_WORDS.put("有点", 0.7);
        DEGREE_WORDS.put("稍微", 0.6);
        DEGREE_WORDS.put("一般", 0.5);
        DEGREE_WORDS.put("极其", 1.6);
        DEGREE_WORDS.put("格外", 1.4);
        DEGREE_WORDS.put("相当", 1.2);
        DEGREE_WORDS.put("略微", 0.7);
        DEGREE_WORDS.put("几乎", 0.6);
    }

    // 否定词
    private static final Set<String> NEGATION_WORDS = new HashSet<>(Arrays.asList(
        "不", "没", "无", "非", "否", "别", "莫", "勿", "未", "不要", "不能",
        "不会", "不该", "不可", "不必", "不用", "不须", "不消", "不须", "不消"
    ));

    /**
     * 分析评论情感
     * @param text 评论内容
     * @return 情感得分 (0-1之间，0表示最消极，1表示最积极)
     */
    public double analyzeSentiment(String text) {
        if (text == null || text.trim().isEmpty()) {
            return 0.5; // 中性
        }

        // 分词
        List<Term> terms = HanLP.segment(text);
        
        double positiveScore = 0;
        double negativeScore = 0;
        double degreeMultiplier = 1.0;
        boolean isNegated = false;
        int wordCount = 0;
        int consecutiveNegations = 0;

        for (int i = 0; i < terms.size(); i++) {
            Term term = terms.get(i);
            String word = term.word;
            if (word.length() < 2) continue; // 跳过单字词

            // 检查程度副词
            if (DEGREE_WORDS.containsKey(word)) {
                degreeMultiplier = DEGREE_WORDS.get(word);
                continue;
            }

            // 检查否定词
            if (NEGATION_WORDS.contains(word)) {
                consecutiveNegations++;
                isNegated = (consecutiveNegations % 2 == 1); // 偶数次否定等于不否定
                continue;
            }

            // 检查情感词
            if (POSITIVE_WORDS.contains(word)) {
                wordCount++;
                double score = isNegated ? -1.0 : 1.0;
                score *= degreeMultiplier;
                if (score > 0) {
                    positiveScore += score;
                } else {
                    negativeScore += Math.abs(score);
                }
                isNegated = false;
                consecutiveNegations = 0;
            } else if (NEGATIVE_WORDS.contains(word)) {
                wordCount++;
                double score = isNegated ? 1.0 : -1.0;
                score *= degreeMultiplier;
                if (score > 0) {
                    positiveScore += score;
                } else {
                    negativeScore += Math.abs(score);
                }
                isNegated = false;
                consecutiveNegations = 0;
            }

            // 重置程度词
            degreeMultiplier = 1.0;
        }

        if (wordCount == 0) {
            return 0.5; // 中性
        }

        // 计算情感得分
        double totalScore = positiveScore + negativeScore;
        if (totalScore == 0) {
            return 0.5; // 中性
        }

        // 归一化到0-1之间
        double score = positiveScore / totalScore;
        return Math.max(0.0, Math.min(1.0, score));
    }

    /**
     * 批量分析评论情感
     * @param comments 评论列表
     * @return 评论ID到情感得分的映射
     */
    public Map<Long, Double> analyzeCommentsSentiment(List<Map<String, Object>> comments) {
        Map<Long, Double> results = new HashMap<>();
        
        for (Map<String, Object> comment : comments) {
            Long id = ((Number) comment.get("id")).longValue();
            String content = (String) comment.get("content");
            results.put(id, analyzeSentiment(content));
        }
        
        return results;
    }
} 