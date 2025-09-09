-- Funnel conversion: Loaded → Interact → Clicks → Purchase by device
WITH step_counts AS (
    SELECT 
        device,
        event_name,
        COUNT(DISTINCT user_id) AS users
    FROM events
    WHERE event_name IN ('Loaded', 'Interact', 'Clicks', 'Purchase')
    GROUP BY device, event_name
),
ordered_steps AS (
    SELECT
        device,
        event_name,
        users,
        ROW_NUMBER() OVER (PARTITION BY device ORDER BY 
            CASE event_name 
                WHEN 'Loaded' THEN 1
                WHEN 'Interact' THEN 2
                WHEN 'Clicks' THEN 3
                WHEN 'Purchase' THEN 4 END
        ) AS step_order
    FROM step_counts
)
SELECT
    event_name AS step,
    users,
    ROUND(100.0 * users / LAG(users) OVER (PARTITION BY device ORDER BY step_order), 2) AS conv_from_prev_pct,
    ROUND(100.0 * users / FIRST_VALUE(users) OVER (PARTITION BY device ORDER BY step_order), 2) AS conv_from_start_pct,
    device
FROM ordered_steps
ORDER BY device, step_order;

-- Possible drop-off reasons:
-- 1. Slow app/web load time.
-- 2. Poor product clarity before clicking.
-- 3. Checkout/payment friction.
