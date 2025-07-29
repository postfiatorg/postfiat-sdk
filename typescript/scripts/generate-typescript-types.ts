#!/usr/bin/env node
/**
 * Generate TypeScript types and utilities from protobuf definitions
 * 
 * This script follows the same patterns as the Python generation scripts,
 * creating TypeScript equivalents of enums, exceptions, and utilities.
 */

import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

// Get the current directory
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Check if generated protobuf files exist
const generatedPath = path.join(__dirname, '..', 'src', 'generated');
if (!fs.existsSync(generatedPath)) {
  console.error('❌ Generated protobuf files not found');
  console.error('Make sure to run: npm run generate');
  process.exit(1);
}

/**
 * Extract enum definitions from generated protobuf TypeScript files
 */
function extractEnumsFromGeneratedFiles(): Array<{name: string, values: Array<{name: string, value: number}>}> {
  const enums: Array<{name: string, values: Array<{name: string, value: number}>}> = [];
  
  // Recursively find all _pb.ts files in the generated directory
  function findProtoFiles(dir: string): string[] {
    const files: string[] = [];
    const entries = fs.readdirSync(dir);
    
    for (const entry of entries) {
      const fullPath = path.join(dir, entry);
      const stat = fs.statSync(fullPath);
      
      if (stat.isDirectory()) {
        files.push(...findProtoFiles(fullPath));
      } else if (entry.endsWith('_pb.ts')) {
        files.push(fullPath);
      }
    }
    
    return files;
  }
  
  const protoFiles = findProtoFiles(generatedPath);
  
  for (const filePath of protoFiles) {
    try {
      const content = fs.readFileSync(filePath, 'utf-8');
      
      // Regex to match enum definitions: export enum EnumName { ... }
      const enumPattern = /export enum (\w+) \{([\s\S]*?)\}/g;
      let enumMatch;
      
      while ((enumMatch = enumPattern.exec(content)) !== null) {
        const enumName = enumMatch[1];
        const enumBody = enumMatch[2];
        
        // Extract enum values: VALUE_NAME = number, (more precise)
        // This regex only matches direct assignments in the enum body
        const valuePattern = /^\s*(\w+) = (\d+),?\s*$/gm;
        const values: Array<{name: string, value: number}> = [];
        let valueMatch;
        
        while ((valueMatch = valuePattern.exec(enumBody)) !== null) {
          const valueName = valueMatch[1];
          const valueNumber = parseInt(valueMatch[2], 10);
          values.push({ name: valueName, value: valueNumber });
        }
        
        if (values.length > 0) {
          // Check if we already have this enum, and merge values if so
          const existingEnum = enums.find(e => e.name === enumName);
          if (existingEnum) {
            // Merge values, avoiding duplicates
            for (const newValue of values) {
              const existingValue = existingEnum.values.find(v => v.name === newValue.name);
              if (!existingValue) {
                existingEnum.values.push(newValue);
              }
            }
          } else {
            enums.push({ name: enumName, values });
          }
        }
      }
    } catch (error) {
      console.warn(`⚠️ Failed to parse ${filePath}: ${error}`);
    }
  }
  
  return enums;
}

/**
 * Generate TypeScript enums from protobuf definitions
 */
function generateEnumsFromProto(): boolean {
  console.log('🔍 Generating TypeScript enums from protobuf definitions...');

  // Check if the postfiat directory exists
  const postfiatPath = path.join(generatedPath, 'postfiat', 'v3');
  if (!fs.existsSync(postfiatPath)) {
    console.error('❌ No generated protobuf files found');
    return false;
  }

  // Find all generated protobuf files
  const protoFiles = fs.readdirSync(postfiatPath).filter(file => file.endsWith('_pb.ts'));
  
  if (protoFiles.length === 0) {
    console.error('❌ No generated protobuf files found in postfiat/v3');
    return false;
  }

  console.log(`📝 Found ${protoFiles.length} protobuf files: ${protoFiles.join(', ')}`);

  // Start building the enums code
  let enumsCode = `/**
 * Auto-generated TypeScript enums from protobuf definitions.
 *
 * DO NOT EDIT - This file is auto-generated from proto files.
 * Run 'npm run generate:types' to regenerate.
 */

`;

  // Dynamically extract enum definitions from generated protobuf files
  const knownEnums = extractEnumsFromGeneratedFiles();

  if (knownEnums.length === 0) {
    console.error('❌ No enums found in generated protobuf files');
    return false;
  }

  console.log(`📝 Found ${knownEnums.length} enums: ${knownEnums.map(e => e.name).join(', ')}`);

  // Generate enum types
  for (const enumDef of knownEnums) {
    console.log(`📝 Generating ${enumDef.name} with ${enumDef.values.length} values`);
    
    enumsCode += `export enum ${enumDef.name} {\n`;
    for (const value of enumDef.values) {
      enumsCode += `  ${value.name} = ${value.value},\n`;
    }
    enumsCode += `}\n\n`;

    // Generate utility functions for each enum
    enumsCode += `export namespace ${enumDef.name} {\n`;
    enumsCode += `  /**\n`;
    enumsCode += `   * Convert from protobuf enum to TypeScript enum\n`;
    enumsCode += `   */\n`;
    enumsCode += `  export function fromProtobuf(value: number): ${enumDef.name} {\n`;
    enumsCode += `    return value as ${enumDef.name};\n`;
    enumsCode += `  }\n\n`;
    
    enumsCode += `  /**\n`;
    enumsCode += `   * Convert from TypeScript enum to protobuf enum\n`;
    enumsCode += `   */\n`;
    enumsCode += `  export function toProtobuf(value: ${enumDef.name}): number {\n`;
    enumsCode += `    return value as number;\n`;
    enumsCode += `  }\n\n`;
    
    enumsCode += `  /**\n`;
    enumsCode += `   * Get all enum values\n`;
    enumsCode += `   */\n`;
    enumsCode += `  export function values(): ${enumDef.name}[] {\n`;
    enumsCode += `    return [\n`;
    for (const value of enumDef.values) {
      enumsCode += `      ${enumDef.name}.${value.name},\n`;
    }
    enumsCode += `    ];\n`;
    enumsCode += `  }\n\n`;
    
    enumsCode += `  /**\n`;
    enumsCode += `   * Get enum name from value\n`;
    enumsCode += `   */\n`;
    enumsCode += `  export function getName(value: ${enumDef.name}): string {\n`;
    enumsCode += `    return ${enumDef.name}[value];\n`;
    enumsCode += `  }\n`;
    enumsCode += `}\n\n`;
  }

  // Write the generated file
  const outputPath = path.join(__dirname, '..', 'src', 'types', 'enums.ts');
  const outputDir = path.dirname(outputPath);
  
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  
  fs.writeFileSync(outputPath, enumsCode);
  console.log(`✅ Generated ${outputPath}`);
  return true;
}

/**
 * Generate TypeScript exceptions from protobuf definitions
 */
function generateExceptions(): boolean {
  console.log('🔍 Generating TypeScript exceptions from protobuf definitions...');

  const exceptionsCode = `/**
 * Auto-generated TypeScript exceptions from protobuf definitions.
 *
 * DO NOT EDIT - This file is auto-generated from proto files.
 * Run 'npm run generate:types' to regenerate.
 */

import { ErrorCode } from './enums';

/**
 * Base interface for error details
 */
export interface ErrorDetails {
  [key: string]: any;
}

/**
 * Base PostFiat error class
 */
export class PostFiatError extends Error {
  public readonly errorCode?: ErrorCode;
  public readonly category?: string;
  public readonly severity?: string;
  public readonly details?: ErrorDetails;
  public readonly field?: string;
  public readonly errorId?: string;

  constructor(
    message: string,
    options?: {
      errorCode?: ErrorCode;
      category?: string;
      severity?: string;
      details?: ErrorDetails;
      field?: string;
      errorId?: string;
    }
  ) {
    super(message);
    this.name = 'PostFiatError';
    this.errorCode = options?.errorCode;
    this.category = options?.category;
    this.severity = options?.severity || 'ERROR';
    this.details = options?.details;
    this.field = options?.field;
    this.errorId = options?.errorId;

    // Ensure proper prototype chain
    Object.setPrototypeOf(this, PostFiatError.prototype);
  }

  /**
   * Convert exception to dictionary representation
   */
  toDict(): Record<string, any> {
    return {
      message: this.message,
      errorCode: this.errorCode,
      category: this.category,
      severity: this.severity,
      details: this.details,
      field: this.field,
      errorId: this.errorId
    };
  }

  /**
   * Convert exception to JSON string
   */
  toJSON(): string {
    return JSON.stringify(this.toDict());
  }
}

/**
 * Client-side error
 */
export class ClientError extends PostFiatError {
  constructor(message: string, options?: Omit<ConstructorParameters<typeof PostFiatError>[1], 'category'>) {
    super(message, { ...options, category: 'CLIENT' });
    this.name = 'ClientError';
    Object.setPrototypeOf(this, ClientError.prototype);
  }
}

/**
 * Server-side error
 */
export class ServerError extends PostFiatError {
  constructor(message: string, options?: Omit<ConstructorParameters<typeof PostFiatError>[1], 'category'>) {
    super(message, { ...options, category: 'SERVER' });
    this.name = 'ServerError';
    Object.setPrototypeOf(this, ServerError.prototype);
  }
}

/**
 * Network communication error
 */
export class NetworkError extends PostFiatError {
  constructor(message: string, options?: Omit<ConstructorParameters<typeof PostFiatError>[1], 'category'>) {
    super(message, { ...options, category: 'NETWORK' });
    this.name = 'NetworkError';
    Object.setPrototypeOf(this, NetworkError.prototype);
  }
}

/**
 * Authentication error
 */
export class AuthError extends PostFiatError {
  constructor(message: string, options?: Omit<ConstructorParameters<typeof PostFiatError>[1], 'category'>) {
    super(message, { ...options, category: 'AUTH' });
    this.name = 'AuthError';
    Object.setPrototypeOf(this, AuthError.prototype);
  }
}

/**
 * Validation error
 */
export class ValidationError extends PostFiatError {
  constructor(message: string, options?: Omit<ConstructorParameters<typeof PostFiatError>[1], 'category'>) {
    super(message, { ...options, category: 'VALIDATION' });
    this.name = 'ValidationError';
    Object.setPrototypeOf(this, ValidationError.prototype);
  }
}

/**
 * Configuration error
 */
export class ConfigurationError extends PostFiatError {
  constructor(message: string, options?: Omit<ConstructorParameters<typeof PostFiatError>[1], 'category'>) {
    super(message, { ...options, category: 'CONFIGURATION' });
    this.name = 'ConfigurationError';
    Object.setPrototypeOf(this, ConfigurationError.prototype);
  }
}

/**
 * Business logic error
 */
export class BusinessError extends PostFiatError {
  constructor(message: string, options?: Omit<ConstructorParameters<typeof PostFiatError>[1], 'category'>) {
    super(message, { ...options, category: 'BUSINESS' });
    this.name = 'BusinessError';
    Object.setPrototypeOf(this, BusinessError.prototype);
  }
}

/**
 * External service error
 */
export class ExternalError extends PostFiatError {
  constructor(message: string, options?: Omit<ConstructorParameters<typeof PostFiatError>[1], 'category'>) {
    super(message, { ...options, category: 'EXTERNAL' });
    this.name = 'ExternalError';
    Object.setPrototypeOf(this, ExternalError.prototype);
  }
}

// Specific error classes
export class AuthenticationError extends AuthError {
  constructor(message: string, options?: Omit<ConstructorParameters<typeof AuthError>[1], 'errorCode'>) {
    super(message, { ...options, errorCode: ErrorCode.AUTHENTICATION_FAILED });
    this.name = 'AuthenticationError';
    Object.setPrototypeOf(this, AuthenticationError.prototype);
  }
}

export class AuthorizationError extends AuthError {
  constructor(message: string, options?: Omit<ConstructorParameters<typeof AuthError>[1], 'errorCode'>) {
    super(message, { ...options, errorCode: ErrorCode.AUTHORIZATION_FAILED });
    this.name = 'AuthorizationError';
    Object.setPrototypeOf(this, AuthorizationError.prototype);
  }
}

export class ValidationFailedError extends ValidationError {
  constructor(message: string, options?: Omit<ConstructorParameters<typeof ValidationError>[1], 'errorCode'>) {
    super(message, { ...options, errorCode: ErrorCode.VALIDATION_FAILED });
    this.name = 'ValidationFailedError';
    Object.setPrototypeOf(this, ValidationFailedError.prototype);
  }
}

export class ResourceNotFoundError extends ClientError {
  constructor(message: string, options?: Omit<ConstructorParameters<typeof ClientError>[1], 'errorCode'>) {
    super(message, { ...options, errorCode: ErrorCode.RESOURCE_NOT_FOUND });
    this.name = 'ResourceNotFoundError';
    Object.setPrototypeOf(this, ResourceNotFoundError.prototype);
  }
}

export class InternalServerError extends ServerError {
  constructor(message: string, options?: Omit<ConstructorParameters<typeof ServerError>[1], 'errorCode'>) {
    super(message, { ...options, errorCode: ErrorCode.INTERNAL_SERVER_ERROR });
    this.name = 'InternalServerError';
    Object.setPrototypeOf(this, InternalServerError.prototype);
  }
}

export class ServiceUnavailableError extends ServerError {
  constructor(message: string, options?: Omit<ConstructorParameters<typeof ServerError>[1], 'errorCode'>) {
    super(message, { ...options, errorCode: ErrorCode.SERVICE_UNAVAILABLE });
    this.name = 'ServiceUnavailableError';
    Object.setPrototypeOf(this, ServiceUnavailableError.prototype);
  }
}

export class RateLimitError extends ServerError {
  constructor(message: string, options?: Omit<ConstructorParameters<typeof ServerError>[1], 'errorCode'>) {
    super(message, { ...options, errorCode: ErrorCode.RATE_LIMIT_EXCEEDED });
    this.name = 'RateLimitError';
    Object.setPrototypeOf(this, RateLimitError.prototype);
  }
}

export class TimeoutError extends ServerError {
  constructor(message: string, options?: Omit<ConstructorParameters<typeof ServerError>[1], 'errorCode'>) {
    super(message, { ...options, errorCode: ErrorCode.TIMEOUT });
    this.name = 'TimeoutError';
    Object.setPrototypeOf(this, TimeoutError.prototype);
  }
}

export class ConnectionError extends NetworkError {
  constructor(message: string, options?: Omit<ConstructorParameters<typeof NetworkError>[1], 'errorCode'>) {
    super(message, { ...options, errorCode: ErrorCode.CONNECTION_FAILED });
    this.name = 'ConnectionError';
    Object.setPrototypeOf(this, ConnectionError.prototype);
  }
}

/**
 * Create appropriate exception instance based on error code
 */
export function createExceptionFromErrorCode(
  errorCode: ErrorCode,
  message: string,
  options?: Omit<ConstructorParameters<typeof PostFiatError>[1], 'errorCode'>
): PostFiatError {
  const exceptionMap: Record<ErrorCode, new (message: string, options?: any) => PostFiatError> = {
    [ErrorCode.AUTHENTICATION_FAILED]: AuthenticationError,
    [ErrorCode.AUTHORIZATION_FAILED]: AuthorizationError,
    [ErrorCode.VALIDATION_FAILED]: ValidationFailedError,
    [ErrorCode.RESOURCE_NOT_FOUND]: ResourceNotFoundError,
    [ErrorCode.INTERNAL_SERVER_ERROR]: InternalServerError,
    [ErrorCode.SERVICE_UNAVAILABLE]: ServiceUnavailableError,
    [ErrorCode.RATE_LIMIT_EXCEEDED]: RateLimitError,
    [ErrorCode.TIMEOUT]: TimeoutError,
    [ErrorCode.CONNECTION_FAILED]: ConnectionError,
    [ErrorCode.OK]: PostFiatError,
    [ErrorCode.UNKNOWN]: PostFiatError,
  };

  const ExceptionClass = exceptionMap[errorCode] || PostFiatError;
  return new ExceptionClass(message, { ...options, errorCode });
}

/**
 * Create exception from error info dictionary
 */
export function createExceptionFromErrorInfo(errorInfo: {
  code?: ErrorCode;
  message?: string;
  context?: ErrorDetails;
  field?: string;
  errorId?: string;
  severity?: string;
}): PostFiatError {
  return createExceptionFromErrorCode(
    errorInfo.code || ErrorCode.UNKNOWN,
    errorInfo.message || 'Unknown error',
    {
      severity: errorInfo.severity,
      details: errorInfo.context,
      field: errorInfo.field,
      errorId: errorInfo.errorId
    }
  );
}
`;

  // Write the generated file
  const outputPath = path.join(__dirname, '..', 'src', 'types', 'exceptions.ts');
  const outputDir = path.dirname(outputPath);
  
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  
  fs.writeFileSync(outputPath, exceptionsCode);
  console.log(`✅ Generated ${outputPath}`);
  return true;
}

/**
 * Generate TypeScript client utilities
 */
function generateClientUtilities(): boolean {
  console.log('🔍 Generating TypeScript client utilities...');

  const clientCode = `/**
 * Auto-generated TypeScript client utilities.
 *
 * DO NOT EDIT - This file is auto-generated from proto files.
 * Run 'npm run generate:types' to regenerate.
 */

import { createConnectTransport } from '@connectrpc/connect-web';
import { createPromiseClient } from '@connectrpc/connect';
import type { Transport } from '@connectrpc/connect';

/**
 * Configuration for the PostFiat client
 */
export interface ClientConfig {
  baseUrl: string;
  timeout?: number;
  headers?: Record<string, string>;
  interceptors?: any[];
}

/**
 * Base client class for PostFiat services
 */
export class PostFiatClient {
  private transport: Transport;
  private config: ClientConfig;

  constructor(config: ClientConfig) {
    this.config = config;
    this.transport = createConnectTransport({
      baseUrl: config.baseUrl,
      interceptors: config.interceptors
    });
  }

  /**
   * Create a promise client for a service
   */
  protected createClient<T>(service: any): T {
    return createPromiseClient(service, this.transport) as T;
  }

  /**
   * Get the transport instance
   */
  getTransport(): Transport {
    return this.transport;
  }

  /**
   * Get the client configuration
   */
  getConfig(): ClientConfig {
    return { ...this.config };
  }
}

/**
 * Default client configuration
 */
export const defaultClientConfig: Partial<ClientConfig> = {
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    'User-Agent': 'PostFiat-TypeScript-SDK/0.1.0'
  }
};

/**
 * Create a PostFiat client with default configuration
 */
export function createPostFiatClient(config: ClientConfig): PostFiatClient {
  const fullConfig = { ...defaultClientConfig, ...config };
  return new PostFiatClient(fullConfig);
}
`;

  // Write the generated file
  const outputPath = path.join(__dirname, '..', 'src', 'client', 'base.ts');
  const outputDir = path.dirname(outputPath);
  
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  
  fs.writeFileSync(outputPath, clientCode);
  console.log(`✅ Generated ${outputPath}`);
  return true;
}

/**
 * Generate React hooks for the SDK
 */
function generateReactHooks(): boolean {
  console.log('🔍 Generating React hooks...');

  const hooksCode = `/**
 * Auto-generated React hooks for PostFiat SDK.
 *
 * DO NOT EDIT - This file is auto-generated from proto files.
 * Run 'npm run generate:types' to regenerate.
 */

import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { PostFiatClient, ClientConfig } from '../client/base';
import { PostFiatError } from '../types/exceptions';

/**
 * PostFiat client context
 */
const PostFiatClientContext = createContext<PostFiatClient | null>(null);

/**
 * PostFiat client provider props
 */
export interface PostFiatClientProviderProps {
  config: ClientConfig;
  children: React.ReactNode;
}

/**
 * PostFiat client provider component
 */
export function PostFiatClientProvider({ config, children }: PostFiatClientProviderProps) {
  const [client] = useState(() => new PostFiatClient(config));

  return (
    <PostFiatClientContext.Provider value={client}>
      {children}
    </PostFiatClientContext.Provider>
  );
}

/**
 * Hook to get the PostFiat client
 */
export function usePostFiatClient(): PostFiatClient {
  const client = useContext(PostFiatClientContext);
  if (!client) {
    throw new Error('usePostFiatClient must be used within a PostFiatClientProvider');
  }
  return client;
}

/**
 * State for async operations
 */
export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: PostFiatError | null;
}

/**
 * Hook for async operations with loading and error states
 */
export function useAsyncOperation<T>(): [
  AsyncState<T>,
  (operation: () => Promise<T>) => Promise<void>
] {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    loading: false,
    error: null
  });

  const execute = useCallback(async (operation: () => Promise<T>) => {
    setState({ data: null, loading: true, error: null });
    try {
      const result = await operation();
      setState({ data: result, loading: false, error: null });
    } catch (error) {
      const postFiatError = error instanceof PostFiatError 
        ? error 
        : new PostFiatError(error instanceof Error ? error.message : 'Unknown error');
      setState({ data: null, loading: false, error: postFiatError });
    }
  }, []);

  return [state, execute];
}

/**
 * Hook for wallet operations
 */
export function useWallet() {
  const [walletState, executeWalletOperation] = useAsyncOperation<any>();

  const createWallet = useCallback(async (request: any) => {
    await executeWalletOperation(async () => {
      // TODO: Implement wallet creation when service is generated
      console.log('Creating wallet:', request);
      return { id: 'wallet_' + Date.now(), ...request };
    });
  }, [executeWalletOperation]);

  const getBalance = useCallback(async (walletId: string) => {
    await executeWalletOperation(async () => {
      // TODO: Implement balance retrieval when service is generated
      console.log('Getting balance for wallet:', walletId);
      return { walletId, balance: 100.50, currency: 'USD' };
    });
  }, [executeWalletOperation]);

  return {
    ...walletState,
    createWallet,
    getBalance
  };
}

/**
 * Hook for message operations
 */
export function useMessages() {
  const [messageState, executeMessageOperation] = useAsyncOperation<any>();

  const sendMessage = useCallback(async (message: any) => {
    await executeMessageOperation(async () => {
      // TODO: Implement message sending when service is generated
      console.log('Sending message:', message);
      return { id: 'msg_' + Date.now(), ...message, timestamp: new Date() };
    });
  }, [executeMessageOperation]);

  const getMessages = useCallback(async (conversationId: string) => {
    await executeMessageOperation(async () => {
      // TODO: Implement message retrieval when service is generated
      console.log('Getting messages for conversation:', conversationId);
      return [];
    });
  }, [executeMessageOperation]);

  return {
    ...messageState,
    sendMessage,
    getMessages
  };
}

/**
 * Hook for real-time subscriptions
 */
export function useSubscription<T>(
  subscribe: () => Promise<AsyncIterable<T>>,
  deps: React.DependencyList = []
): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    loading: true,
    error: null
  });

  useEffect(() => {
    let cancelled = false;

    const startSubscription = async () => {
      try {
        const subscription = await subscribe();
        
        if (cancelled) return;
        
        setState({ data: null, loading: false, error: null });
        
        for await (const value of subscription) {
          if (cancelled) break;
          setState({ data: value, loading: false, error: null });
        }
      } catch (error) {
        if (cancelled) return;
        
        const postFiatError = error instanceof PostFiatError 
          ? error 
          : new PostFiatError(error instanceof Error ? error.message : 'Subscription error');
        setState({ data: null, loading: false, error: postFiatError });
      }
    };

    startSubscription();

    return () => {
      cancelled = true;
    };
  }, deps);

  return state;
}
`;

  // Write the generated file
  const outputPath = path.join(__dirname, '..', 'src', 'hooks', 'index.tsx');
  const outputDir = path.dirname(outputPath);
  
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  
  fs.writeFileSync(outputPath, hooksCode);
  console.log(`✅ Generated ${outputPath}`);
  return true;
}

/**
 * Generate generated/index.ts file for protobuf re-exports
 */
function generateGeneratedIndex(): boolean {
  console.log('🔍 Generating generated/index.ts file...');

  const generatedIndexCode = `// Auto-generated exports for protobuf files
// Re-export with aliases to avoid conflicts with our custom enums
export {
  MessageType as ProtoMessageType,
  EncryptionMode as ProtoEncryptionMode,
  KeyType,
} from './postfiat/v3/messages_pb';
export {
  ErrorCode as ProtoErrorCode,
  ErrorSeverity as ProtoErrorSeverity,
  ErrorCategory as ProtoErrorCategory,
} from './postfiat/v3/errors_pb';
export * from './a2a/v1/a2a_pb';
export * from './a2a/v1/a2a_connect';

// Runtime class exports for PostFiat types
export {
  Envelope,
  ContextReference,
  MultiPartMessagePart,
  CoreMessage,
  PostFiatAgentCapabilities,
  PostFiatEnvelopePayload,
  PostFiatA2AMessage,
  AccessGrant,
} from './postfiat/v3/messages_pb';

// Type-only exports for additional type safety
export type {
  Envelope as EnvelopeType,
  ContextReference as ContextReferenceType,
  MultiPartMessagePart as MultiPartMessagePartType,
  CoreMessage as CoreMessageType,
  PostFiatAgentCapabilities as PostFiatAgentCapabilitiesType,
  PostFiatEnvelopePayload as PostFiatEnvelopePayloadType,
  PostFiatA2AMessage as PostFiatA2AMessageType,
  AccessGrant as AccessGrantType,
} from './postfiat/v3/messages_pb';
`;

  // Write the generated/index.ts file
  const generatedDir = path.join(__dirname, '..', 'src', 'generated');
  if (!fs.existsSync(generatedDir)) {
    fs.mkdirSync(generatedDir, { recursive: true });
  }
  
  const outputPath = path.join(generatedDir, 'index.ts');
  fs.writeFileSync(outputPath, generatedIndexCode);
  console.log(`✅ Generated ${outputPath}`);
  return true;
}

/**
 * Generate main index file
 */
function generateIndex(): boolean {
  console.log('🔍 Generating main index file...');

  const indexCode = `/**
 * PostFiat TypeScript SDK
 * 
 * Auto-generated from protobuf definitions.
 * DO NOT EDIT - This file is auto-generated from proto files.
 * Run 'npm run generate:types' to regenerate.
 */

// Types and enums
export * from './types/enums';
export * from './types/exceptions';

// Client utilities
export * from './client/base';

// React hooks (optional peer dependency)
export * from './hooks';

// Generated protobuf types and services
export * from './generated';

// Version
export const VERSION = '0.1.0';

// Default export
export { createPostFiatClient } from './client/base';
`;

  // Write the generated file
  const outputPath = path.join(__dirname, '..', 'src', 'index.ts');
  
  fs.writeFileSync(outputPath, indexCode);
  console.log(`✅ Generated ${outputPath}`);
  return true;
}

/**
 * Main function to generate all TypeScript types
 */
function main(): void {
  console.log('🔄 Generating TypeScript types from protobuf definitions...');

  let success = true;
  success = generateEnumsFromProto() && success;
  success = generateExceptions() && success;
  success = generateClientUtilities() && success;
  success = generateReactHooks() && success;
  success = generateGeneratedIndex() && success;
  success = generateIndex() && success;

  if (success) {
    console.log('✅ All TypeScript types generated successfully!');
  } else {
    console.log('❌ Some files failed to generate');
    process.exit(1);
  }
}

// Run the main function
main();