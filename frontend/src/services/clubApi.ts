/**
 * Club Analysis API Client
 * Methods for fetching club stats and member data
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
    constructor(message: string, public statusCode: number) {
        super(message);
        this.name = 'ApiError';
    }
}

export interface ClubMember {
    tag: string;
    name: string;
    trophies: number;
    role: string;
    rank: number;
}

export interface ClubStats {
    tag: string;
    name: string;
    description: string;
    total_trophies: number;
    required_trophies: number;
    member_count: number;
    average_trophies: number;
    median_trophies: number;
    top_player: ClubMember | null;
    type: string;
}

export interface MemberComparison {
    member: ClubMember;
    vs_average: number;
    vs_median: number;
    percentile: number;
}

/**
 * Get comprehensive club statistics
 */
export async function getClubStats(clubTag: string): Promise<ClubStats> {
    // Remove # if present
    const cleanTag = clubTag.replace('#', '');

    try {
        const response = await fetch(`${API_BASE_URL}/api/clubs/${cleanTag}`);

        if (!response.ok) {
            throw new ApiError(
                `Failed to fetch club stats: ${response.statusText}`,
                response.status
            );
        }

        return await response.json();
    } catch (error) {
        if (error instanceof ApiError) throw error;
        throw new ApiError(
            error instanceof Error ? error.message : 'Unknown error fetching club',
            500
        );
    }
}

/**
 * Get ranked list of club members
 */
export async function getClubMembers(clubTag: string): Promise<{ members: ClubMember[]; total: number }> {
    const cleanTag = clubTag.replace('#', '');

    try {
        const response = await fetch(`${API_BASE_URL}/api/clubs/${cleanTag}/members`);

        if (!response.ok) {
            throw new ApiError(
                `Failed to fetch club members: ${response.statusText}`,
                response.status
            );
        }

        return await response.json();
    } catch (error) {
        if (error instanceof ApiError) throw error;
        throw new ApiError(
            error instanceof Error ? error.message : 'Unknown error fetching members',
            500
        );
    }
}

/**
 * Compare a member against club averages
 */
export async function compareMember(
    clubTag: string,
    memberTag: string
): Promise<MemberComparison> {
    const cleanClubTag = clubTag.replace('#', '');
    const cleanMemberTag = memberTag.replace('#', '');

    try {
        const response = await fetch(
            `${API_BASE_URL}/api/clubs/${cleanClubTag}/compare/${cleanMemberTag}`
        );

        if (!response.ok) {
            throw new ApiError(
                `Failed to compare member: ${response.statusText}`,
                response.status
            );
        }

        return await response.json();
    } catch (error) {
        if (error instanceof ApiError) throw error;
        throw new ApiError(
            error instanceof Error ? error.message : 'Unknown error comparing member',
            500
        );
    }
}

export const clubService = {
    getClubStats,
    getClubMembers,
    compareMember,
};
