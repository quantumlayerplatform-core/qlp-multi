# QLP Frontend Architecture Guide

## Executive Summary

This document outlines the frontend architecture for the Quantum Layer Platform (QLP), an AI-powered code generation platform. The frontend provides a modern, responsive interface for users to generate production-ready code through natural language, monitor workflows, and manage their projects.

## Technology Stack

### Core Framework
- **Next.js 14** (App Router) - Full-stack React framework with server-side rendering
- **TypeScript** - Type safety and better developer experience
- **React 18** - UI component library with concurrent features

### Styling & UI
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/ui** - High-quality, customizable component library
- **Framer Motion** - Animation library for smooth interactions
- **Lucide Icons** - Modern icon set

### State Management & Data Fetching
- **React Query (TanStack Query)** - Server state management
- **Zustand** - Client state management (lightweight alternative to Redux)
- **SWR** - Alternative data fetching library for real-time updates

### Authentication
- **Clerk** - Complete user management solution
  - Already integrated in backend
  - Supports social logins, magic links, passwords
  - Built-in user profile management
  - Team/organization support

### Real-time Features
- **Server-Sent Events (SSE)** - For workflow status updates
- **WebSockets** (optional) - For bidirectional communication
- **React Hot Toast** - Real-time notifications

### Development Tools
- **ESLint** - Code linting
- **Prettier** - Code formatting
- **Husky** - Git hooks for code quality
- **Jest & React Testing Library** - Testing

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Browser                              │
├─────────────────────────────────────────────────────────────┤
│                    Next.js Frontend                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Pages     │  │  Components  │  │   API Routes     │  │
│  │  (App Dir)  │  │  (React/TS)  │  │  (Middleware)    │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              State Management Layer                  │   │
│  │  React Query  │  Zustand  │  Context API           │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                     API Client Layer                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │   Fetch  │  │    SSE   │  │ WebSocket│  │  Clerk   │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    QLP Backend (Port 8000)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Orchestrator │  │ Agent Factory│  │ Validation Mesh │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
qlp-frontend/
├── app/                          # Next.js App Router
│   ├── (auth)/                   # Auth group route
│   │   ├── sign-in/             
│   │   │   └── [[...sign-in]]/  # Clerk sign-in
│   │   ├── sign-up/
│   │   │   └── [[...sign-up]]/  # Clerk sign-up
│   │   └── layout.tsx           # Auth layout
│   │
│   ├── (dashboard)/             # Dashboard group route
│   │   ├── layout.tsx           # Dashboard layout with sidebar
│   │   ├── page.tsx             # Dashboard home
│   │   ├── generate/            # Code generation
│   │   │   ├── page.tsx         # Generation form
│   │   │   └── [id]/            # Generation details
│   │   ├── projects/            # Projects/Capsules
│   │   │   ├── page.tsx         # Projects list
│   │   │   └── [id]/            # Project details
│   │   ├── workflows/           # Workflow monitoring
│   │   │   ├── page.tsx         # Workflows list
│   │   │   └── [id]/            # Workflow details
│   │   ├── templates/           # Template library
│   │   ├── settings/            # User settings
│   │   └── api-docs/            # API documentation
│   │
│   ├── api/                     # API routes
│   │   ├── webhooks/            # Webhook handlers
│   │   │   └── clerk/           # Clerk webhooks
│   │   └── health/              # Health check
│   │
│   ├── layout.tsx               # Root layout
│   ├── page.tsx                 # Landing page
│   ├── globals.css              # Global styles
│   └── providers.tsx            # App providers
│
├── components/                   # React components
│   ├── ui/                      # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   ├── form.tsx
│   │   ├── input.tsx
│   │   ├── select.tsx
│   │   ├── textarea.tsx
│   │   └── ...
│   │
│   ├── forms/                   # Form components
│   │   ├── GenerationForm.tsx
│   │   ├── ProjectSettingsForm.tsx
│   │   └── GitHubIntegrationForm.tsx
│   │
│   ├── workflows/               # Workflow components
│   │   ├── WorkflowStatus.tsx
│   │   ├── WorkflowTimeline.tsx
│   │   ├── ActivityLog.tsx
│   │   └── WorkflowActions.tsx
│   │
│   ├── projects/                # Project components
│   │   ├── ProjectCard.tsx
│   │   ├── ProjectList.tsx
│   │   ├── CapsuleViewer.tsx
│   │   └── DownloadButton.tsx
│   │
│   ├── shared/                  # Shared components
│   │   ├── Header.tsx
│   │   ├── Sidebar.tsx
│   │   ├── Footer.tsx
│   │   ├── LoadingSpinner.tsx
│   │   ├── ErrorBoundary.tsx
│   │   └── EmptyState.tsx
│   │
│   └── charts/                  # Analytics components
│       ├── UsageChart.tsx
│       ├── PerformanceMetrics.tsx
│       └── CostBreakdown.tsx
│
├── hooks/                       # Custom React hooks
│   ├── useAuth.ts              # Clerk auth hook
│   ├── useGeneration.ts        # Code generation
│   ├── useWorkflow.ts          # Workflow monitoring
│   ├── useCapsules.ts          # Capsule management
│   ├── useRealtime.ts          # SSE/WebSocket
│   ├── useToast.ts             # Toast notifications
│   └── useDebounce.ts          # Debouncing hook
│
├── lib/                        # Library code
│   ├── api/                    # API client
│   │   ├── client.ts           # Base API client
│   │   ├── generation.ts       # Generation endpoints
│   │   ├── projects.ts         # Project endpoints
│   │   ├── workflows.ts        # Workflow endpoints
│   │   └── types.ts            # API types
│   │
│   ├── utils/                  # Utility functions
│   │   ├── format.ts           # Formatters
│   │   ├── validators.ts       # Form validators
│   │   ├── constants.ts        # App constants
│   │   └── helpers.ts          # Helper functions
│   │
│   ├── clerk.ts                # Clerk configuration
│   ├── query-client.ts         # React Query setup
│   └── store.ts                # Zustand store
│
├── types/                      # TypeScript types
│   ├── api.ts                  # API response types
│   ├── generation.ts           # Generation types
│   ├── project.ts              # Project types
│   ├── workflow.ts             # Workflow types
│   └── user.ts                 # User types
│
├── styles/                     # Additional styles
│   └── animations.css          # Custom animations
│
├── public/                     # Static assets
│   ├── images/
│   ├── fonts/
│   └── favicon.ico
│
├── tests/                      # Test files
│   ├── components/
│   ├── hooks/
│   └── utils/
│
└── config files               # Configuration
    ├── .env.local             # Environment variables
    ├── next.config.js         # Next.js config
    ├── tailwind.config.ts     # Tailwind config
    ├── tsconfig.json          # TypeScript config
    ├── package.json           # Dependencies
    └── middleware.ts          # Next.js middleware
```

## Key Pages & User Flows

### 1. Landing Page (`/`)
**Purpose**: Convert visitors to users
- Hero section with value proposition
- Feature highlights with animations
- Pricing tiers
- Customer testimonials
- CTA buttons → Sign up/Sign in

### 2. Dashboard (`/dashboard`)
**Purpose**: Central hub for all activities
- Quick stats (projects created, tokens used, etc.)
- Recent projects grid
- Quick action buttons
- Usage chart
- Notifications/alerts

### 3. Code Generation (`/generate`)
**Purpose**: Main value delivery
```typescript
// Key components
- Natural language input (textarea)
- Template selector (optional)
- Advanced options accordion:
  - Programming language
  - Tier selection (T0-T3)
  - GitHub integration toggle
  - Enterprise features
- Real-time cost estimation
- Generate button → Workflow tracking
```

### 4. Workflow Monitor (`/workflows/[id]`)
**Purpose**: Real-time progress tracking
```typescript
// Real-time updates via SSE
- Progress bar with stages
- Activity timeline
- Live logs (collapsible)
- Error handling with retry
- Success actions:
  - Download capsule
  - Push to GitHub
  - View code
```

### 5. Project Details (`/projects/[id]`)
**Purpose**: Manage generated projects
- Project metadata
- File explorer
- Code viewer with syntax highlighting
- Version history
- Actions:
  - Download (ZIP/TAR)
  - Push to GitHub
  - Share
  - Delete

## API Integration

### Base API Client
```typescript
// lib/api/client.ts
import { getAuth } from '@clerk/nextjs/server';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class APIClient {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const { getToken } = getAuth();
    const token = await getToken();

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new APIError(response.status, await response.text());
    }

    return response.json();
  }

  // Core methods
  async generateCode(data: GenerationRequest): Promise<GenerationResponse> {
    return this.request('/execute', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getWorkflowStatus(id: string): Promise<WorkflowStatus> {
    return this.request(`/workflow/status/${id}`);
  }

  async getCapsule(id: string): Promise<Capsule> {
    return this.request(`/capsule/${id}`);
  }

  // ... more methods
}

export const api = new APIClient();
```

### React Query Integration
```typescript
// hooks/useGeneration.ts
import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api/client';

export function useGenerateCode() {
  return useMutation({
    mutationFn: api.generateCode,
    onSuccess: (data) => {
      // Redirect to workflow monitor
      router.push(`/workflows/${data.workflow_id}`);
    },
  });
}

export function useWorkflowStatus(workflowId: string) {
  return useQuery({
    queryKey: ['workflow', workflowId],
    queryFn: () => api.getWorkflowStatus(workflowId),
    refetchInterval: 2000, // Poll every 2s
    enabled: !!workflowId,
  });
}
```

### Real-time Updates
```typescript
// hooks/useRealtime.ts
export function useWorkflowStream(workflowId: string) {
  const [status, setStatus] = useState<WorkflowStatus | null>(null);

  useEffect(() => {
    if (!workflowId) return;

    const eventSource = new EventSource(
      `${API_BASE}/workflow/status/${workflowId}/stream`
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStatus(data);
    };

    eventSource.onerror = () => {
      eventSource.close();
      // Fallback to polling
    };

    return () => eventSource.close();
  }, [workflowId]);

  return status;
}
```

## Component Examples

### Generation Form Component
```typescript
// components/forms/GenerationForm.tsx
export function GenerationForm() {
  const { mutate, isLoading } = useGenerateCode();
  const form = useForm<GenerationInput>({
    resolver: zodResolver(generationSchema),
    defaultValues: {
      description: '',
      tier_override: 'T1',
      push_to_github: false,
    },
  });

  const onSubmit = (data: GenerationInput) => {
    mutate({
      ...data,
      metadata: {
        push_to_github: data.push_to_github,
        github_repo_name: data.github_repo_name,
      },
    });
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>What would you like to build?</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Create a REST API for user management with JWT auth..."
                  className="min-h-[120px]"
                  {...field}
                />
              </FormControl>
              <FormDescription>
                Describe your project in natural language
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* More fields... */}

        <Button type="submit" disabled={isLoading} size="lg">
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Sparkles className="mr-2 h-4 w-4" />
              Generate Code
            </>
          )}
        </Button>
      </form>
    </Form>
  );
}
```

### Workflow Status Component
```typescript
// components/workflows/WorkflowStatus.tsx
export function WorkflowStatus({ workflowId }: { workflowId: string }) {
  const status = useWorkflowStream(workflowId);

  if (!status) {
    return <LoadingSpinner />;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Workflow Progress</CardTitle>
        <CardDescription>
          Status: {status.status}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Progress value={status.progress} className="mb-4" />
        
        <div className="space-y-2">
          {status.activities.map((activity, i) => (
            <div key={i} className="flex items-center gap-2">
              {activity.status === 'completed' ? (
                <CheckCircle className="h-4 w-4 text-green-500" />
              ) : activity.status === 'running' ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Circle className="h-4 w-4 text-gray-300" />
              )}
              <span className="text-sm">{activity.name}</span>
            </div>
          ))}
        </div>

        {status.status === 'completed' && (
          <div className="mt-6 flex gap-2">
            <Button asChild>
              <Link href={`/projects/${status.capsule_id}`}>
                View Project
              </Link>
            </Button>
            <Button variant="outline">
              <Download className="mr-2 h-4 w-4" />
              Download
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

## State Management

### Zustand Store
```typescript
// lib/store.ts
import { create } from 'zustand';

interface AppState {
  // User preferences
  theme: 'light' | 'dark';
  defaultTier: string;
  
  // UI state
  sidebarOpen: boolean;
  
  // Actions
  setTheme: (theme: 'light' | 'dark') => void;
  toggleSidebar: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  theme: 'light',
  defaultTier: 'T1',
  sidebarOpen: true,
  
  setTheme: (theme) => set({ theme }),
  toggleSidebar: () => set((state) => ({ 
    sidebarOpen: !state.sidebarOpen 
  })),
}));
```

## Performance Optimization

### 1. Code Splitting
```typescript
// Dynamic imports for heavy components
const CodeEditor = dynamic(() => import('@/components/CodeEditor'), {
  loading: () => <LoadingSpinner />,
  ssr: false,
});
```

### 2. Image Optimization
```typescript
import Image from 'next/image';

<Image
  src="/hero-image.png"
  alt="QLP Platform"
  width={1200}
  height={600}
  priority
  placeholder="blur"
/>
```

### 3. API Response Caching
```typescript
// React Query caching strategy
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      refetchOnWindowFocus: false,
    },
  },
});
```

### 4. Bundle Size Optimization
```javascript
// next.config.js
module.exports = {
  experimental: {
    optimizePackageImports: ['lucide-react', '@radix-ui/react-icons'],
  },
  images: {
    formats: ['image/avif', 'image/webp'],
  },
};
```

## Deployment Strategy

### Environment Configuration
```bash
# .env.local (development)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxx
CLERK_SECRET_KEY=sk_test_xxx
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000

# .env.production
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_xxx
CLERK_SECRET_KEY=sk_live_xxx
NEXT_PUBLIC_API_URL=https://api.qlp.ai
NEXT_PUBLIC_APP_URL=https://app.qlp.ai
```

### Build & Deployment
```bash
# Build for production
npm run build

# Start production server
npm start

# Docker deployment
docker build -t qlp-frontend .
docker run -p 3000:3000 qlp-frontend

# Vercel deployment (recommended)
vercel --prod
```

### CI/CD Pipeline
```yaml
# .github/workflows/deploy.yml
name: Deploy Frontend

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run tests
        run: npm test
      
      - name: Build
        run: npm run build
        env:
          NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: ${{ secrets.CLERK_PUBLISHABLE_KEY }}
      
      - name: Deploy to Vercel
        uses: vercel/action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-args: '--prod'
```

## Security Considerations

### 1. Authentication
- All routes protected by Clerk middleware
- API requests include JWT tokens
- Role-based access control (RBAC)

### 2. Input Validation
- Client-side validation with Zod
- Server-side validation in API routes
- XSS prevention via React's built-in escaping

### 3. API Security
- Rate limiting on API routes
- CORS configuration
- CSRF protection

### 4. Content Security Policy
```typescript
// middleware.ts
export function middleware(request: NextRequest) {
  const response = NextResponse.next();
  
  response.headers.set(
    'Content-Security-Policy',
    "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline';"
  );
  
  return response;
}
```

## Monitoring & Analytics

### 1. Performance Monitoring
- Vercel Analytics (built-in)
- Google Analytics 4
- Custom performance metrics

### 2. Error Tracking
- Sentry integration
- Custom error boundaries
- User feedback collection

### 3. Usage Analytics
```typescript
// Track key events
export function trackEvent(event: string, properties?: any) {
  // Google Analytics
  gtag('event', event, properties);
  
  // Custom analytics
  api.analytics.track({ event, properties });
}

// Usage
trackEvent('code_generated', {
  language: 'python',
  tier: 'T2',
  token_count: 1500,
});
```

## Development Workflow

### Getting Started
```bash
# Clone repository
git clone https://github.com/your-org/qlp-frontend.git
cd qlp-frontend

# Install dependencies
npm install

# Set up environment
cp .env.example .env.local
# Edit .env.local with your keys

# Run development server
npm run dev

# Open http://localhost:3000
```

### Development Commands
```bash
# Development
npm run dev          # Start dev server
npm run build        # Build for production
npm start           # Start production server

# Code Quality
npm run lint        # Run ESLint
npm run lint:fix    # Fix linting issues
npm run format      # Format with Prettier
npm run typecheck   # TypeScript check

# Testing
npm test           # Run tests
npm run test:watch # Watch mode
npm run test:ci    # CI mode

# Storybook (if added)
npm run storybook   # Component development
npm run build-storybook
```

## Future Enhancements

### Phase 1 (MVP) ✓
- Basic authentication
- Code generation form
- Workflow monitoring
- Project management
- Download functionality

### Phase 2 (Current)
- Real-time updates
- GitHub integration UI
- Template library
- Advanced options
- Mobile responsive

### Phase 3 (Planned)
- Team collaboration
- Template marketplace
- API playground
- Visual workflow builder
- Code editor integration
- Multi-language UI
- Offline support
- PWA features

### Phase 4 (Future)
- AI chat assistant
- Voice input
- Code review features
- Integration marketplace
- White-label options
- Enterprise SSO
- Advanced analytics
- Cost optimization tools

## Support & Resources

### Documentation
- [Next.js Documentation](https://nextjs.org/docs)
- [Clerk Documentation](https://clerk.com/docs)
- [shadcn/ui Components](https://ui.shadcn.com)
- [React Query](https://tanstack.com/query/latest)

### Internal Resources
- API Documentation: `/api-docs`
- Component Storybook: `http://localhost:6006`
- Design System: `/design-system`

### Getting Help
- GitHub Issues: Report bugs
- Discord: Community support
- Email: support@qlp.ai

---

**Document Version**: 1.0  
**Last Updated**: July 2025  
**Maintained By**: QLP Frontend Team