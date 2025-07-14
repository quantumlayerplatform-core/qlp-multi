-- HAP (Hate, Abuse, Profanity) Detection Tables
-- Migration: 004_create_hap_tables.sql

-- Table for logging violations
CREATE TABLE IF NOT EXISTS hap_violations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    context VARCHAR(50) NOT NULL, -- user_request, agent_output, etc.
    severity VARCHAR(20) NOT NULL, -- clean, low, medium, high, critical
    categories TEXT[], -- Array of categories detected
    confidence DECIMAL(3, 2), -- 0.00 to 1.00
    content_hash VARCHAR(64), -- SHA-256 hash of content
    explanation TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes will be created separately
);

-- Table for custom rules per tenant
CREATE TABLE IF NOT EXISTS hap_custom_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    rule_name VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    pattern TEXT NOT NULL, -- Regex pattern
    severity VARCHAR(20) NOT NULL,
    enabled BOOLEAN DEFAULT true,
    description TEXT,
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(tenant_id, rule_name),
    INDEX idx_hap_rules_tenant (tenant_id, enabled)
);

-- Table for whitelisted terms per tenant
CREATE TABLE IF NOT EXISTS hap_whitelist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    term VARCHAR(255) NOT NULL,
    context VARCHAR(50), -- Optional context restriction
    reason TEXT,
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(tenant_id, term, context),
    INDEX idx_hap_whitelist_tenant (tenant_id)
);

-- Table for user risk scores
CREATE TABLE IF NOT EXISTS hap_user_risk_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    risk_score DECIMAL(3, 2) DEFAULT 0.00, -- 0.00 to 1.00
    total_violations INTEGER DEFAULT 0,
    critical_violations INTEGER DEFAULT 0,
    high_violations INTEGER DEFAULT 0,
    last_violation_at TIMESTAMP WITH TIME ZONE,
    flagged_for_review BOOLEAN DEFAULT false,
    notes TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(tenant_id, user_id),
    INDEX idx_hap_risk_score (risk_score DESC),
    INDEX idx_hap_flagged (flagged_for_review, updated_at DESC)
);

-- Summary statistics table (updated periodically)
CREATE TABLE IF NOT EXISTS hap_statistics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    total_checks INTEGER DEFAULT 0,
    total_violations INTEGER DEFAULT 0,
    violations_by_severity JSONB DEFAULT '{}',
    violations_by_category JSONB DEFAULT '{}',
    violations_by_context JSONB DEFAULT '{}',
    top_violating_users JSONB DEFAULT '[]',
    average_confidence DECIMAL(3, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(tenant_id, period_start, period_end),
    INDEX idx_hap_stats_period (tenant_id, period_start DESC)
);

-- Function to update user risk scores
CREATE OR REPLACE FUNCTION update_user_risk_score()
RETURNS TRIGGER AS $$
BEGIN
    -- Update or insert user risk score
    INSERT INTO hap_user_risk_scores (
        tenant_id, user_id, risk_score, total_violations,
        critical_violations, high_violations, last_violation_at
    )
    VALUES (
        NEW.tenant_id,
        NEW.user_id,
        CASE 
            WHEN NEW.severity = 'critical' THEN 0.9
            WHEN NEW.severity = 'high' THEN 0.7
            WHEN NEW.severity = 'medium' THEN 0.5
            ELSE 0.3
        END,
        1,
        CASE WHEN NEW.severity = 'critical' THEN 1 ELSE 0 END,
        CASE WHEN NEW.severity = 'high' THEN 1 ELSE 0 END,
        NEW.created_at
    )
    ON CONFLICT (tenant_id, user_id) DO UPDATE SET
        risk_score = LEAST(
            1.0,
            hap_user_risk_scores.risk_score + 
            CASE 
                WHEN NEW.severity = 'critical' THEN 0.3
                WHEN NEW.severity = 'high' THEN 0.2
                WHEN NEW.severity = 'medium' THEN 0.1
                ELSE 0.05
            END
        ),
        total_violations = hap_user_risk_scores.total_violations + 1,
        critical_violations = hap_user_risk_scores.critical_violations + 
            CASE WHEN NEW.severity = 'critical' THEN 1 ELSE 0 END,
        high_violations = hap_user_risk_scores.high_violations + 
            CASE WHEN NEW.severity = 'high' THEN 1 ELSE 0 END,
        last_violation_at = NEW.created_at,
        updated_at = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic risk score updates
CREATE TRIGGER trigger_update_risk_score
AFTER INSERT ON hap_violations
FOR EACH ROW
WHEN (NEW.user_id IS NOT NULL)
EXECUTE FUNCTION update_user_risk_score();

-- View for recent violations
CREATE OR REPLACE VIEW hap_recent_violations AS
SELECT 
    v.id,
    v.tenant_id,
    v.user_id,
    v.context,
    v.severity,
    v.categories,
    v.confidence,
    v.explanation,
    v.created_at,
    u.risk_score as user_risk_score,
    u.total_violations as user_total_violations
FROM hap_violations v
LEFT JOIN hap_user_risk_scores u 
    ON v.tenant_id = u.tenant_id AND v.user_id = u.user_id
WHERE v.created_at > NOW() - INTERVAL '24 hours'
ORDER BY v.created_at DESC;

-- View for high-risk users
CREATE OR REPLACE VIEW hap_high_risk_users AS
SELECT 
    u.tenant_id,
    u.user_id,
    u.risk_score,
    u.total_violations,
    u.critical_violations,
    u.high_violations,
    u.last_violation_at,
    u.flagged_for_review,
    COUNT(DISTINCT v.categories) as unique_violation_types
FROM hap_user_risk_scores u
LEFT JOIN hap_violations v 
    ON u.tenant_id = v.tenant_id AND u.user_id = v.user_id
WHERE u.risk_score >= 0.7 OR u.flagged_for_review = true
GROUP BY u.tenant_id, u.user_id, u.risk_score, u.total_violations,
         u.critical_violations, u.high_violations, u.last_violation_at,
         u.flagged_for_review
ORDER BY u.risk_score DESC;

-- Grant permissions
GRANT SELECT, INSERT ON hap_violations TO qlp_user;
GRANT SELECT, INSERT, UPDATE ON hap_custom_rules TO qlp_user;
GRANT SELECT, INSERT, UPDATE ON hap_whitelist TO qlp_user;
GRANT SELECT, INSERT, UPDATE ON hap_user_risk_scores TO qlp_user;
GRANT SELECT, INSERT ON hap_statistics TO qlp_user;
GRANT SELECT ON hap_recent_violations TO qlp_user;
GRANT SELECT ON hap_high_risk_users TO qlp_user;