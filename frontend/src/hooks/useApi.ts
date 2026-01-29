/**
 * Generic useApi Hook
 * Simplifies API calls with loading, error, and data management
 */

import { useState, useEffect, useCallback } from 'react';
import { useToast } from '../context/ToastContext';

interface UseApiOptions<T> {
    onSuccess?: (data: T) => void;
    onError?: (error: Error) => void;
    showErrorToast?: boolean;
    showSuccessToast?: boolean;
    successMessage?: string;
}

interface UseApiResult<T> {
    data: T | null;
    error: Error | null;
    loading: boolean;
    refetch: () => Promise<void>;
    mutate: (newData: T) => void;
}

export function useApi<T>(
    apiFunction: () => Promise<T>,
    dependencies: React.DependencyList = [],
    options: UseApiOptions<T> = {}
): UseApiResult<T> {
    const [data, setData] = useState<T | null>(null);
    const [error, setError] = useState<Error | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const { showError, showSuccess } = useToast();

    const {
        onSuccess,
        onError,
        showErrorToast = true,
        showSuccessToast = false,
        successMessage,
    } = options;

    const fetchData = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const result = await apiFunction();
            setData(result);

            if (showSuccessToast && successMessage) {
                showSuccess(successMessage);
            }

            onSuccess?.(result);
        } catch (err) {
            const errorObj = err instanceof Error ? err : new Error('An error occurred');
            setError(errorObj);

            if (showErrorToast) {
                showError(errorObj.message);
            }

            onError?.(errorObj);
        } finally {
            setLoading(false);
        }
    }, [apiFunction, onSuccess, onError, showErrorToast, showSuccessToast, successMessage, showError, showSuccess]);

    useEffect(() => {
        fetchData();
    }, dependencies);

    const mutate = useCallback((newData: T) => {
        setData(newData);
    }, []);

    return {
        data,
        error,
        loading,
        refetch: fetchData,
        mutate,
    };
}

/**
 * useApiMutation Hook
 * For API calls triggered by user actions (POST, PUT, DELETE)
 */
interface UseApiMutationOptions<T> {
    onSuccess?: (data: T) => void;
    onError?: (error: Error) => void;
    showErrorToast?: boolean;
    showSuccessToast?: boolean;
    successMessage?: string;
}

interface UseApiMutationResult<T, P> {
    data: T | null;
    error: Error | null;
    loading: boolean;
    mutate: (params: P) => Promise<T | null>;
    reset: () => void;
}

export function useApiMutation<T, P>(
    apiFunction: (params: P) => Promise<T>,
    options: UseApiMutationOptions<T> = {}
): UseApiMutationResult<T, P> {
    const [data, setData] = useState<T | null>(null);
    const [error, setError] = useState<Error | null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const { showError, showSuccess } = useToast();

    const {
        onSuccess,
        onError,
        showErrorToast = true,
        showSuccessToast = false,
        successMessage,
    } = options;

    const mutate = useCallback(async (params: P): Promise<T | null> => {
        setLoading(true);
        setError(null);

        try {
            const result = await apiFunction(params);
            setData(result);

            if (showSuccessToast && successMessage) {
                showSuccess(successMessage);
            }

            onSuccess?.(result);
            return result;
        } catch (err) {
            const errorObj = err instanceof Error ? err : new Error('An error occurred');
            setError(errorObj);

            if (showErrorToast) {
                showError(errorObj.message);
            }

            onError?.(errorObj);
            return null;
        } finally {
            setLoading(false);
        }
    }, [apiFunction, onSuccess, onError, showErrorToast, showSuccessToast, successMessage, showError, showSuccess]);

    const reset = useCallback(() => {
        setData(null);
        setError(null);
        setLoading(false);
    }, []);

    return {
        data,
        error,
        loading,
        mutate,
        reset,
    };
}
