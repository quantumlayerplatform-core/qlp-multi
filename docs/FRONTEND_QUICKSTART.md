# QLP Frontend Quick Start Guide

## 🚀 Get Started in 5 Minutes

This guide will help you set up the QLP frontend quickly with minimal configuration.

## Prerequisites

- Node.js 20+ installed
- npm or yarn package manager
- QLP backend running on `http://localhost:8000`
- Clerk account for authentication

## Step 1: Create Next.js App

```bash
# Create new Next.js app with TypeScript and Tailwind
npx create-next-app@latest qlp-frontend --typescript --tailwind --app --use-npm

# Navigate to project
cd qlp-frontend
```

## Step 2: Install Dependencies

```bash
# Core dependencies
npm install @clerk/nextjs @tanstack/react-query zustand axios

# UI components
npm install @radix-ui/react-dialog @radix-ui/react-select @radix-ui/react-tabs
npm install lucide-react react-hot-toast
npm install tailwind-merge clsx class-variance-authority

# Development dependencies
npm install -D @types/node prettier eslint-config-prettier
```

## Step 3: Set Up shadcn/ui

```bash
# Initialize shadcn/ui
npx shadcn-ui@latest init

# When prompted:
# - Would you like to use TypeScript? → Yes
# - Which style would you like to use? → Default
# - Which color would you like to use? → Slate
# - Where is your global CSS file? → app/globals.css
# - Would you like to use CSS variables? → Yes
# - Where is your tailwind.config.js? → tailwind.config.ts
# - Configure import alias? → src/*

# Add essential components
npx shadcn-ui@latest add button card dialog form input select textarea toast
```

## Step 4: Environment Setup

Create `.env.local`:

```bash
# Clerk Authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_YOUR_KEY
CLERK_SECRET_KEY=sk_test_YOUR_KEY

# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000

# Optional: GitHub Integration
NEXT_PUBLIC_GITHUB_CLIENT_ID=your_github_client_id
```

## Step 5: Configure Clerk

Create `app/layout.tsx`:

```typescript
import { Inter } from 'next/font/google'
import { ClerkProvider } from '@clerk/nextjs'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'QLP - AI Code Generation Platform',
  description: 'Generate production-ready code with AI',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className={inter.className}>{children}</body>
      </html>
    </ClerkProvider>
  )
}
```

Create `middleware.ts`:

```typescript
import { authMiddleware } from "@clerk/nextjs";

export default authMiddleware({
  publicRoutes: ["/", "/sign-in", "/sign-up"],
});

export const config = {
  matcher: ["/((?!.+\\.[\\w]+$|_next).*)", "/", "/(api|trpc)(.*)"],
};
```

## Step 6: Create Basic Pages

### Landing Page (`app/page.tsx`):

```typescript
import Link from 'next/link'
import { Button } from '@/components/ui/button'

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center">
      <div className="mx-auto max-w-2xl text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
          Generate Production Code with AI
        </h1>
        <p className="mt-6 text-lg leading-8 text-gray-600">
          Transform your ideas into production-ready applications in minutes, 
          not months. Powered by advanced AI agents.
        </p>
        <div className="mt-10 flex items-center justify-center gap-x-6">
          <Link href="/sign-up">
            <Button size="lg">Get Started</Button>
          </Link>
          <Link href="/sign-in">
            <Button variant="outline" size="lg">Sign In</Button>
          </Link>
        </div>
      </div>
    </div>
  )
}
```

### Sign In Page (`app/sign-in/[[...sign-in]]/page.tsx`):

```typescript
import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <SignIn />
    </div>
  );
}
```

### Dashboard Layout (`app/(dashboard)/layout.tsx`):

```typescript
import { UserButton } from "@clerk/nextjs";
import Link from "next/link";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="border-b bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center">
              <Link href="/dashboard" className="text-xl font-bold">
                QLP Platform
              </Link>
              <div className="ml-10 flex items-baseline space-x-4">
                <Link
                  href="/dashboard"
                  className="rounded-md px-3 py-2 text-sm font-medium hover:bg-gray-100"
                >
                  Dashboard
                </Link>
                <Link
                  href="/generate"
                  className="rounded-md px-3 py-2 text-sm font-medium hover:bg-gray-100"
                >
                  Generate
                </Link>
                <Link
                  href="/projects"
                  className="rounded-md px-3 py-2 text-sm font-medium hover:bg-gray-100"
                >
                  Projects
                </Link>
              </div>
            </div>
            <UserButton afterSignOutUrl="/" />
          </div>
        </div>
      </nav>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {children}
      </main>
    </div>
  );
}
```

### Dashboard Page (`app/(dashboard)/dashboard/page.tsx`):

```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function DashboardPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-8">Dashboard</h1>
      
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 mb-8">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Total Projects
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">0</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Tokens Used
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">0</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Active Workflows
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">0</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Success Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">-</p>
          </CardContent>
        </Card>
      </div>
      
      <div className="flex justify-center">
        <Link href="/generate">
          <Button size="lg">Generate New Project</Button>
        </Link>
      </div>
    </div>
  );
}
```

## Step 7: Create API Client

Create `lib/api-client.ts`:

```typescript
import axios from 'axios';
import { useAuth } from '@clerk/nextjs';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create axios instance
export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Custom hook for authenticated requests
export function useApiClient() {
  const { getToken } = useAuth();

  const client = axios.create({
    baseURL: API_BASE,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Add auth interceptor
  client.interceptors.request.use(async (config) => {
    const token = await getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  return client;
}

// API functions
export const api = {
  // Generate code
  generateCode: async (data: any, token?: string) => {
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    return apiClient.post('/execute', data, { headers });
  },

  // Get workflow status
  getWorkflowStatus: async (workflowId: string, token?: string) => {
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    return apiClient.get(`/workflow/status/${workflowId}`, { headers });
  },

  // Get capsule
  getCapsule: async (capsuleId: string, token?: string) => {
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    return apiClient.get(`/capsule/${capsuleId}`, { headers });
  },

  // Download capsule
  downloadCapsule: async (capsuleId: string, format: string = 'zip', token?: string) => {
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    return apiClient.get(`/api/capsules/${capsuleId}/download?format=${format}`, {
      headers,
      responseType: 'blob',
    });
  },
};
```

## Step 8: Create Generation Form

Create `app/(dashboard)/generate/page.tsx`:

```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { useToast } from '@/components/ui/use-toast';
import { api } from '@/lib/api-client';

export default function GeneratePage() {
  const router = useRouter();
  const { getToken } = useAuth();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [description, setDescription] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!description.trim()) {
      toast({
        title: 'Error',
        description: 'Please enter a project description',
        variant: 'destructive',
      });
      return;
    }

    setLoading(true);
    
    try {
      const token = await getToken();
      const response = await api.generateCode({
        description,
        requirements: 'Production-ready code with tests and documentation',
        tier_override: 'T1',
        user_id: 'user-1',
        tenant_id: 'default',
      }, token);

      toast({
        title: 'Success',
        description: 'Code generation started!',
      });

      // Redirect to workflow monitor
      router.push(`/workflows/${response.data.workflow_id}`);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to generate code. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-8">Generate Code</h1>
      
      <Card>
        <CardHeader>
          <CardTitle>Describe Your Project</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="description">Project Description</Label>
              <Textarea
                id="description"
                placeholder="Create a REST API for user management with JWT authentication..."
                className="min-h-[150px] mt-2"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? 'Generating...' : 'Generate Code'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
```

## Step 9: Run the Application

```bash
# Start the development server
npm run dev

# Open http://localhost:3000
```

## Step 10: Next Steps

### Essential Features to Add:

1. **Workflow Monitoring Page** (`/workflows/[id]`)
   - Real-time status updates
   - Activity timeline
   - Error handling

2. **Projects List** (`/projects`)
   - Grid/list view of generated projects
   - Search and filters
   - Quick actions

3. **Project Details** (`/projects/[id]`)
   - File explorer
   - Code viewer
   - Download options

4. **React Query Setup**
   ```bash
   npm install @tanstack/react-query
   ```

5. **Toast Notifications**
   ```bash
   npx shadcn-ui@latest add toast
   ```

### Quick Component Templates:

#### Loading Spinner
```typescript
export function LoadingSpinner() {
  return (
    <div className="flex justify-center items-center p-4">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
    </div>
  );
}
```

#### Error State
```typescript
export function ErrorState({ message }: { message: string }) {
  return (
    <div className="text-center p-4">
      <p className="text-red-600">{message}</p>
    </div>
  );
}
```

#### Empty State
```typescript
export function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center p-4 text-gray-500">
      <p>{message}</p>
    </div>
  );
}
```

## Troubleshooting

### Common Issues:

1. **Clerk Authentication Error**
   - Verify your Clerk keys in `.env.local`
   - Check Clerk dashboard for correct configuration

2. **API Connection Error**
   - Ensure backend is running on port 8000
   - Check CORS configuration in backend

3. **TypeScript Errors**
   - Run `npm run typecheck` to identify issues
   - Install missing type definitions

4. **Styling Issues**
   - Ensure Tailwind CSS is properly configured
   - Check `globals.css` imports

## Production Deployment

### Vercel (Recommended)
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Set environment variables in Vercel dashboard
```

### Docker
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package*.json ./
RUN npm ci --only=production
EXPOSE 3000
CMD ["npm", "start"]
```

## Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [Clerk Documentation](https://clerk.com/docs)
- [shadcn/ui Components](https://ui.shadcn.com)
- [Tailwind CSS](https://tailwindcss.com/docs)

---

You now have a working frontend for the QLP platform! 🎉