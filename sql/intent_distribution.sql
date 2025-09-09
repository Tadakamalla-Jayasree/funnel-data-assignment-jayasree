-- Intent distribution and correlation with purchases
WITH intents AS (
    SELECT 
        session_id,
        COALESCE(NULLIF(detected_intent, ''), 'unknown') AS intent
    FROM messages
),
intent_counts AS (
    SELECT
        intent,
        COUNT(*) AS count
    FROM intents
    GROUP BY intent
),
total AS (
    SELECT SUM(count) AS total FROM intent_counts
)
SELECT 
    intent,
    count,
    ROUND(100.0 * count / total, 2) AS pct_of_total
FROM intent_counts, total
ORDER BY count DESC;

-- Top 2 intents correlated with purchases
SELECT 
    i.intent,
    COUNT(DISTINCT o.order_id) AS purchase_count
FROM intents i
JOIN orders o ON i.session_id = o.session_id
GROUP BY i.intent
ORDER BY purchase_count DESC
LIMIT 2;
