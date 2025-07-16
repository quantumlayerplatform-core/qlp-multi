"""
Language detection and handling utilities for agents
Production-grade implementation with comprehensive support
"""

from typing import Dict, Any, Optional, Tuple, List
import re
import structlog

logger = structlog.get_logger()


class LanguageDetector:
    """Production-grade language detection with multiple strategies"""
    
    # Comprehensive language patterns with confidence scoring
    LANGUAGE_PATTERNS = {
        "python": {
            "keywords": ["python", "py", "pip", "poetry", "conda", "venv", "virtualenv"],
            "frameworks": ["flask", "django", "fastapi", "pandas", "numpy", "tensorflow", "pytorch", "scikit", "jupyter", "streamlit", "dash"],
            "extensions": [".py", ".pyx", ".pyw"],
            "confidence": 10
        },
        "javascript": {
            "keywords": ["javascript", "js", "node", "nodejs", "npm", "yarn", "pnpm"],
            "frameworks": ["express", "react", "vue", "angular", "next", "nuxt", "svelte", "webpack", "babel", "jest", "mocha"],
            "extensions": [".js", ".mjs", ".jsx"],
            "confidence": 10
        },
        "typescript": {
            "keywords": ["typescript", "ts", "tsx", "type-safe", "typed"],
            "frameworks": ["angular", "nestjs", "next.js", "deno"],
            "extensions": [".ts", ".tsx", ".d.ts"],
            "confidence": 12  # Higher than JS to prefer TS when both match
        },
        "java": {
            "keywords": ["java", "jvm", "maven", "gradle", "ant"],
            "frameworks": ["spring", "springboot", "hibernate", "struts", "junit", "mockito", "tomcat", "jetty"],
            "extensions": [".java", ".jar", ".class"],
            "confidence": 10
        },
        "go": {
            "keywords": ["go", "golang", "gopher"],
            "frameworks": ["gin", "echo", "fiber", "gorilla", "chi", "beego", "iris", "revel"],
            "extensions": [".go"],
            "confidence": 10
        },
        "rust": {
            "keywords": ["rust", "cargo", "rustc", "rustup"],
            "frameworks": ["actix", "rocket", "warp", "tokio", "serde", "diesel", "yew"],
            "extensions": [".rs"],
            "confidence": 10
        },
        "cpp": {
            "keywords": ["c++", "cpp", "cplusplus"],
            "frameworks": ["boost", "qt", "cmake", "stl", "opencv"],
            "extensions": [".cpp", ".cc", ".cxx", ".hpp", ".h++"],
            "confidence": 9
        },
        "c": {
            "keywords": ["c language", "ansi c", "embedded c", "pure c"],
            "frameworks": ["gtk", "opengl", "sdl"],
            "extensions": [".c", ".h"],
            "confidence": 8  # Lower than C++ to avoid false positives
        },
        "csharp": {
            "keywords": ["c#", "csharp", "dotnet", ".net"],
            "frameworks": ["asp.net", "blazor", "xamarin", "unity", "entityframework", "wpf", "winforms"],
            "extensions": [".cs", ".csx"],
            "confidence": 10
        },
        "php": {
            "keywords": ["php"],
            "frameworks": ["laravel", "symfony", "codeigniter", "wordpress", "drupal", "composer", "yii", "slim"],
            "extensions": [".php", ".phtml"],
            "confidence": 10
        },
        "ruby": {
            "keywords": ["ruby", "rb", "gem", "bundler"],
            "frameworks": ["rails", "sinatra", "rspec", "rake", "capistrano"],
            "extensions": [".rb", ".erb"],
            "confidence": 10
        },
        "swift": {
            "keywords": ["swift", "ios", "macos", "watchos", "tvos"],
            "frameworks": ["swiftui", "uikit", "cocoapods", "carthage", "spm", "vapor"],
            "extensions": [".swift"],
            "confidence": 10
        },
        "kotlin": {
            "keywords": ["kotlin", "kt"],
            "frameworks": ["android", "ktor", "spring", "coroutines", "compose"],
            "extensions": [".kt", ".kts"],
            "confidence": 10
        },
        "scala": {
            "keywords": ["scala"],
            "frameworks": ["akka", "play", "spark", "cats", "zio", "sbt"],
            "extensions": [".scala", ".sc"],
            "confidence": 10
        },
        "r": {
            "keywords": ["r language", "rlang", "rstats"],
            "frameworks": ["tidyverse", "ggplot", "shiny", "dplyr", "caret"],
            "extensions": [".r", ".rmd"],
            "confidence": 10
        },
        "sql": {
            "keywords": ["sql", "query", "database"],
            "frameworks": ["mysql", "postgresql", "sqlite", "oracle", "sqlserver", "mariadb"],
            "extensions": [".sql"],
            "confidence": 8
        },
        "shell": {
            "keywords": ["bash", "shell", "sh", "zsh", "fish", "script"],
            "frameworks": ["unix", "linux", "posix"],
            "extensions": [".sh", ".bash", ".zsh"],
            "confidence": 7
        }
    }
    
    # Context-based defaults
    CONTEXT_DEFAULTS = {
        "web": "javascript",
        "api": "python",
        "data": "python",
        "mobile": "kotlin",
        "ios": "swift",
        "android": "kotlin",
        "system": "python",
        "script": "python",
        "ml": "python",
        "ai": "python",
        "embedded": "c",
        "game": "cpp",
        "enterprise": "java",
        "cloud": "go"
    }
    
    @classmethod
    def detect_language(
        cls,
        description: str = None,
        code: str = None,
        metadata: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> str:
        """
        Comprehensive language detection using multiple strategies
        
        Priority order:
        1. Explicit metadata/context specifications
        2. Code analysis (if provided)
        3. Description analysis with scoring
        4. Context-based defaults
        5. Fallback to Python
        """
        # Check explicit specifications first
        if metadata:
            if lang := metadata.get("language_constraint"):
                logger.info(f"Using explicit language from metadata: {lang}")
                return lang.lower()
            if lang := metadata.get("language"):
                logger.info(f"Using language from metadata: {lang}")
                return lang.lower()
                
        if context:
            if lang := context.get("required_language"):
                logger.info(f"Using required language from context: {lang}")
                return lang.lower()
            if lang := context.get("preferred_language"):
                logger.info(f"Using preferred language from context: {lang}")
                return lang.lower()
        
        # Analyze code if provided
        if code:
            if lang := cls._detect_from_code(code):
                logger.info(f"Detected language from code: {lang}")
                return lang
        
        # Analyze description
        if description:
            if lang := cls._detect_from_description(description):
                logger.info(f"Detected language from description: {lang}")
                return lang
        
        # Use context-based default
        if description:
            if lang := cls._get_context_default(description):
                logger.info(f"Using context-based default: {lang}")
                return lang
        
        # Ultimate fallback
        logger.info("No language detected, defaulting to Python")
        return "python"
    
    @classmethod
    def _detect_from_code(cls, code: str) -> Optional[str]:
        """Detect language from code patterns"""
        if not code:
            return None
            
        # Language-specific patterns with confidence scoring
        patterns = {
            "python": [
                (r'^\s*def\s+\w+\s*\(', 10),
                (r'^\s*class\s+\w+', 10),
                (r'^\s*import\s+\w+', 8),
                (r'^\s*from\s+\w+\s+import', 8),
                (r'if\s+__name__\s*==\s*["\']__main__["\']', 10),
                (r'print\s*\(', 5),
                (r'^\s*@\w+', 7),
                (r':\s*$', 3),
                (r'self\.', 7),
            ],
            "javascript": [
                (r'function\s+\w+\s*\(', 10),
                (r'const\s+\w+\s*=', 8),
                (r'let\s+\w+\s*=', 8),
                (r'var\s+\w+\s*=', 7),
                (r'=>', 8),
                (r'console\.log\s*\(', 7),
                (r'module\.exports', 8),
                (r'require\s*\(', 8),
                (r'async\s+function', 8),
                (r'\.then\s*\(', 7),
            ],
            "typescript": [
                (r':\s*\w+\s*[=;]', 10),  # Type annotations
                (r'interface\s+\w+', 10),
                (r'type\s+\w+\s*=', 10),
                (r'<\w+>', 8),  # Generics
                (r'export\s+interface', 9),
                (r'implements\s+\w+', 9),
            ],
            "java": [
                (r'public\s+class\s+\w+', 10),
                (r'private\s+\w+\s+\w+', 8),
                (r'public\s+static\s+void\s+main', 10),
                (r'import\s+java\.', 9),
                (r'System\.out\.println', 8),
                (r'@Override', 7),
                (r'new\s+\w+\s*\(', 6),
            ],
            "go": [
                (r'package\s+\w+', 10),
                (r'func\s+\w+\s*\(', 10),
                (r'import\s+\(', 8),
                (r'fmt\.Print', 8),
                (r':=', 9),
                (r'go\s+func', 8),
            ],
            "rust": [
                (r'fn\s+\w+\s*\(', 10),
                (r'let\s+mut\s+', 9),
                (r'impl\s+\w+', 8),
                (r'pub\s+fn', 8),
                (r'use\s+\w+::', 8),
                (r'println!\s*\(', 7),
                (r'match\s+\w+\s*\{', 8),
            ],
        }
        
        scores = {}
        for lang, lang_patterns in patterns.items():
            score = 0
            for pattern, weight in lang_patterns:
                if re.search(pattern, code, re.MULTILINE):
                    score += weight
            if score > 0:
                scores[lang] = score
        
        if scores:
            best_lang = max(scores, key=scores.get)
            if scores[best_lang] >= 10:
                return best_lang
        
        return None
    
    @classmethod
    def _detect_from_description(cls, description: str) -> Optional[str]:
        """Detect language from task description with scoring"""
        if not description:
            return None
            
        desc_lower = description.lower()
        language_scores = {}
        
        # Score each language based on pattern matches
        for language, patterns in cls.LANGUAGE_PATTERNS.items():
            score = 0
            
            # Check keywords
            for keyword in patterns["keywords"]:
                if keyword in desc_lower:
                    # Exact language name gets highest score
                    if keyword == language:
                        score += patterns["confidence"]
                    else:
                        score += patterns["confidence"] // 2
            
            # Check frameworks
            for framework in patterns["frameworks"]:
                if framework in desc_lower:
                    score += patterns["confidence"] // 3
            
            # Check file extensions
            for ext in patterns["extensions"]:
                if ext in desc_lower:
                    score += patterns["confidence"] // 4
            
            if score > 0:
                language_scores[language] = score
        
        # Find best match with minimum threshold
        if language_scores:
            best_language = max(language_scores, key=language_scores.get)
            if language_scores[best_language] >= 5:
                return best_language
        
        return None
    
    @classmethod
    def _get_context_default(cls, description: str) -> Optional[str]:
        """Get default language based on context clues"""
        desc_lower = description.lower()
        
        # Check for context keywords
        for context, default_lang in cls.CONTEXT_DEFAULTS.items():
            if context in desc_lower:
                return default_lang
        
        # Check for specific use cases
        use_case_patterns = {
            "api": ["rest", "endpoint", "http", "server", "backend"],
            "web": ["website", "frontend", "ui", "interface"],
            "data": ["analysis", "science", "dataframe", "dataset"],
            "ml": ["machine learning", "neural", "model", "training"],
            "mobile": ["app", "application", "ios", "android"],
            "system": ["script", "automation", "cli", "tool"],
            "enterprise": ["microservice", "distributed", "scalable"]
        }
        
        for use_case, keywords in use_case_patterns.items():
            if any(keyword in desc_lower for keyword in keywords):
                return cls.CONTEXT_DEFAULTS.get(use_case, "python")
        
        return None
    
    @classmethod
    def get_language_safe(cls, language: Optional[str]) -> str:
        """Get language with null safety and validation"""
        if not language:
            return "python"
        
        language = language.lower().strip()
        
        # Validate against known languages
        known_languages = set(cls.LANGUAGE_PATTERNS.keys())
        if language in known_languages:
            return language
        
        # Handle common aliases
        aliases = {
            "node": "javascript",
            "nodejs": "javascript",
            "js": "javascript",
            "ts": "typescript",
            "py": "python",
            "rb": "ruby",
            "rs": "rust",
            "kt": "kotlin",
            "cpp": "cpp",
            "c++": "cpp",
            "cs": "csharp",
            "c#": "csharp",
            "golang": "go",
            "sh": "shell",
            "bash": "shell"
        }
        
        if language in aliases:
            return aliases[language]
        
        logger.warning(f"Unknown language '{language}', defaulting to Python")
        return "python"


def get_language_example(language: str) -> Tuple[str, str, str]:
    """Get language-specific example code for prompting"""
    language = LanguageDetector.get_language_safe(language)
    
    examples = {
        "python": (
            "from fastapi import FastAPI, HTTPException\\nfrom pydantic import BaseModel\\n\\napp = FastAPI()\\n\\nclass User(BaseModel):\\n    name: str\\n    email: str\\n\\n@app.post('/users')\\ndef create_user(user: User):\\n    return {'message': 'User created', 'user': user}",
            "import pytest\\nfrom fastapi.testclient import TestClient\\nfrom main import app\\n\\nclient = TestClient(app)\\n\\ndef test_create_user():\\n    response = client.post('/users', json={'name': 'John', 'email': 'john@example.com'})\\n    assert response.status_code == 200",
            '["fastapi", "pydantic", "pytest"]'
        ),
        "javascript": (
            "const express = require('express');\\nconst app = express();\\n\\napp.use(express.json());\\n\\napp.post('/users', (req, res) => {\\n    const { name, email } = req.body;\\n    res.json({ message: 'User created', user: { name, email } });\\n});\\n\\napp.listen(3000, () => console.log('Server running on port 3000'));",
            "const request = require('supertest');\\nconst app = require('./app');\\n\\ndescribe('POST /users', () => {\\n    it('should create a user', async () => {\\n        const response = await request(app)\\n            .post('/users')\\n            .send({ name: 'John', email: 'john@example.com' });\\n        expect(response.status).toBe(200);\\n    });\\n});",
            '["express", "supertest", "jest"]'
        ),
        "typescript": (
            "import express, { Request, Response } from 'express';\\n\\nconst app = express();\\napp.use(express.json());\\n\\ninterface User {\\n    name: string;\\n    email: string;\\n}\\n\\napp.post('/users', (req: Request, res: Response) => {\\n    const user: User = req.body;\\n    res.json({ message: 'User created', user });\\n});\\n\\napp.listen(3000, () => console.log('Server running on port 3000'));",
            "import request from 'supertest';\\nimport app from './app';\\n\\ndescribe('POST /users', () => {\\n    it('should create a user', async () => {\\n        const response = await request(app)\\n            .post('/users')\\n            .send({ name: 'John', email: 'john@example.com' });\\n        expect(response.status).toBe(200);\\n    });\\n});",
            '["express", "@types/express", "supertest", "@types/supertest", "typescript"]'
        ),
        "java": (
            "import org.springframework.boot.SpringApplication;\\nimport org.springframework.boot.autoconfigure.SpringBootApplication;\\nimport org.springframework.web.bind.annotation.*;\\n\\n@SpringBootApplication\\n@RestController\\npublic class Application {\\n    @PostMapping(\\\"/users\\\")\\n    public String createUser(@RequestBody User user) {\\n        return \\\"User created: \\\" + user.getName();\\n    }\\n\\n    public static void main(String[] args) {\\n        SpringApplication.run(Application.class, args);\\n    }\\n}",
            "import org.junit.jupiter.api.Test;\\nimport org.springframework.boot.test.context.SpringBootTest;\\nimport static org.junit.jupiter.api.Assertions.*;\\n\\n@SpringBootTest\\nclass ApplicationTest {\\n    @Test\\n    void testCreateUser() {\\n        User user = new User(\\\"John\\\", \\\"john@example.com\\\");\\n        assertNotNull(user);\\n    }\\n}",
            '["spring-boot-starter-web", "spring-boot-starter-test"]'
        ),
        "go": (
            "package main\\n\\nimport (\\n    \\\"encoding/json\\\"\\n    \\\"net/http\\\"\\n    \\\"github.com/gin-gonic/gin\\\"\\n)\\n\\ntype User struct {\\n    Name  string `json:\\\"name\\\"`\\n    Email string `json:\\\"email\\\"`\\n}\\n\\nfunc createUser(c *gin.Context) {\\n    var user User\\n    c.ShouldBindJSON(&user)\\n    c.JSON(http.StatusOK, gin.H{\\\"message\\\": \\\"User created\\\", \\\"user\\\": user})\\n}\\n\\nfunc main() {\\n    r := gin.Default()\\n    r.POST(\\\"/users\\\", createUser)\\n    r.Run(\\\":8080\\\")\\n}",
            "package main\\n\\nimport (\\n    \\\"testing\\\"\\n    \\\"net/http/httptest\\\"\\n    \\\"github.com/gin-gonic/gin\\\"\\n)\\n\\nfunc TestCreateUser(t *testing.T) {\\n    gin.SetMode(gin.TestMode)\\n    r := gin.Default()\\n    r.POST(\\\"/users\\\", createUser)\\n    // Add test implementation\\n}",
            '["gin"]'
        ),
        "rust": (
            "use actix_web::{web, App, HttpResponse, HttpServer, Result};\\nuse serde::{Deserialize, Serialize};\\n\\n#[derive(Serialize, Deserialize)]\\nstruct User {\\n    name: String,\\n    email: String,\\n}\\n\\nasync fn create_user(user: web::Json<User>) -> Result<HttpResponse> {\\n    Ok(HttpResponse::Ok().json(serde_json::json!({\\n        \\\"message\\\": \\\"User created\\\",\\n        \\\"user\\\": user.into_inner()\\n    })))\\n}\\n\\n#[actix_web::main]\\nasync fn main() -> std::io::Result<()> {\\n    HttpServer::new(|| {\\n        App::new().route(\\\"/users\\\", web::post().to(create_user))\\n    })\\n    .bind(\\\"127.0.0.1:8080\\\")?\\n    .run()\\n    .await\\n}",
            "#[cfg(test)]\\nmod tests {\\n    use super::*;\\n    use actix_web::{test, web, App};\\n\\n    #[actix_web::test]\\n    async fn test_create_user() {\\n        let app = test::init_service(\\n            App::new().route(\\\"/users\\\", web::post().to(create_user))\\n        ).await;\\n        // Add test implementation\\n    }\\n}",
            '["actix-web", "serde", "serde_json", "tokio"]'
        )
    }
    
    return examples.get(language, examples["python"])


def ensure_language_in_output(output: Dict[str, Any], language: str) -> Dict[str, Any]:
    """Ensure language is properly set in output dictionary"""
    if not isinstance(output, dict):
        output = {"content": str(output)}
    
    # Ensure language is set
    output["language"] = LanguageDetector.get_language_safe(
        output.get("language", language)
    )
    
    # Ensure code field exists if not present
    if "code" not in output:
        # Try to extract from content or other fields
        if "content" in output:
            output["code"] = output["content"]
        else:
            output["code"] = str(output)
    
    return output


def extract_code_from_output(output: Any, language: str = None) -> Tuple[str, str]:
    """
    Extract code and language from various output formats
    Returns: (code, language)
    """
    code = ""
    detected_language = language or "python"
    
    if isinstance(output, dict):
        # Direct code field
        if "code" in output:
            code = output["code"]
        elif "content" in output:
            code = output["content"]
        else:
            code = str(output)
        
        # Language from output
        if "language" in output:
            detected_language = output["language"]
    else:
        code = str(output)
    
    # Clean code from markdown blocks if present
    if "```" in code:
        import re
        # Extract code from markdown
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', code, re.DOTALL)
        if code_blocks:
            code = code_blocks[0].strip()
            # Try to detect language from markdown
            lang_match = re.search(r'```(\w+)\n', code)
            if lang_match and not language:
                detected_language = lang_match.group(1)
    
    return code, LanguageDetector.get_language_safe(detected_language)