-- Multi-tenancy Core Schema
-- Version: 001
-- Description: Initial tenant schema with RLS policies

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum types
CREATE TYPE tenant_plan AS ENUM ('free', 'team', 'enterprise');
CREATE TYPE user_role AS ENUM ('owner', 'admin', 'member', 'guest');
CREATE TYPE workspace_role AS ENUM ('owner', 'admin', 'contributor', 'viewer');

-- Tenants table
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    azure_ad_tenant_id VARCHAR(255) UNIQUE,
    plan tenant_plan NOT NULL DEFAULT 'free',
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Workspaces table
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, name)
);

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    azure_ad_object_id VARCHAR(255) UNIQUE,
    profile JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tenant-User relationship
CREATE TABLE tenant_users (
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role user_role NOT NULL DEFAULT 'member',
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    invited_by UUID REFERENCES users(id),
    is_active BOOLEAN DEFAULT true,
    PRIMARY KEY (tenant_id, user_id)
);

-- Workspace-Member relationship
CREATE TABLE workspace_members (
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role workspace_role NOT NULL DEFAULT 'viewer',
    permissions JSONB DEFAULT '{}',
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    PRIMARY KEY (workspace_id, user_id)
);

-- Indexes for performance
CREATE INDEX idx_tenants_azure_ad_tenant_id ON tenants(azure_ad_tenant_id) WHERE azure_ad_tenant_id IS NOT NULL;
CREATE INDEX idx_tenants_plan ON tenants(plan);
CREATE INDEX idx_tenants_is_active ON tenants(is_active);

CREATE INDEX idx_workspaces_tenant_id ON workspaces(tenant_id);
CREATE INDEX idx_workspaces_is_active ON workspaces(tenant_id, is_active);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_azure_ad_object_id ON users(azure_ad_object_id) WHERE azure_ad_object_id IS NOT NULL;

CREATE INDEX idx_tenant_users_user_id ON tenant_users(user_id);
CREATE INDEX idx_tenant_users_role ON tenant_users(tenant_id, role);
CREATE INDEX idx_tenant_users_is_active ON tenant_users(tenant_id, is_active);

CREATE INDEX idx_workspace_members_user_id ON workspace_members(user_id);
CREATE INDEX idx_workspace_members_workspace_id ON workspace_members(workspace_id);

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update trigger to all tables
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workspaces_updated_at BEFORE UPDATE ON workspaces
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) Policies
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see workspaces they belong to
CREATE POLICY workspace_isolation ON workspaces
    FOR ALL
    USING (
        tenant_id IN (
            SELECT tenant_id 
            FROM tenant_users 
            WHERE user_id = current_setting('app.current_user_id')::UUID
        )
    );

-- Policy: Users can only see workspace members for their workspaces
CREATE POLICY workspace_member_isolation ON workspace_members
    FOR ALL
    USING (
        workspace_id IN (
            SELECT w.id 
            FROM workspaces w
            JOIN tenant_users tu ON w.tenant_id = tu.tenant_id
            WHERE tu.user_id = current_setting('app.current_user_id')::UUID
        )
    );

-- Helper function to set current user context
CREATE OR REPLACE FUNCTION set_current_user(user_id UUID)
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.current_user_id', user_id::text, false);
END;
$$ LANGUAGE plpgsql;

-- Helper function to get current tenant
CREATE OR REPLACE FUNCTION get_current_tenant_id()
RETURNS UUID AS $$
BEGIN
    RETURN (
        SELECT tenant_id 
        FROM tenant_users 
        WHERE user_id = current_setting('app.current_user_id')::UUID
        LIMIT 1
    );
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE tenants IS 'Organizations using the platform';
COMMENT ON TABLE workspaces IS 'Isolated work areas within a tenant';
COMMENT ON TABLE users IS 'Platform users that can belong to multiple tenants';
COMMENT ON TABLE tenant_users IS 'Maps users to tenants with roles';
COMMENT ON TABLE workspace_members IS 'Maps users to workspaces with permissions';

COMMENT ON COLUMN tenants.plan IS 'Subscription plan determining features and limits';
COMMENT ON COLUMN tenants.settings IS 'Tenant-specific configuration and preferences';
COMMENT ON COLUMN workspace_members.permissions IS 'Fine-grained permissions beyond role';