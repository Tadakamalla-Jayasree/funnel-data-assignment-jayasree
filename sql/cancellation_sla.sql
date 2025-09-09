-- SLA check: cancellation allowed within 60 minutes
SELECT 
    COUNT(*) AS total_orders,
    COUNT(canceled_at) AS canceled,
    SUM(CASE WHEN canceled_at IS NOT NULL 
              AND (strftime('%s', canceled_at) - strftime('%s', created_at)) > 3600
             THEN 1 ELSE 0 END) AS violations,
    ROUND(100.0 * SUM(CASE WHEN canceled_at IS NOT NULL 
              AND (strftime('%s', canceled_at) - strftime('%s', created_at)) > 3600
             THEN 1 ELSE 0 END) / COUNT(*), 2) AS violation_rate_pct
FROM orders;
