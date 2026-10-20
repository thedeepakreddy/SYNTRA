import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ApprovalsPage } from '../pages/ApprovalsPage';
import { apiClient } from '../api/client';
import { Approval } from '../types';

const MOCK_APPROVAL: Approval = {
  id: '00000000-0000-0000-0000-000000000099',
  org_id: '00000000-0000-0000-0000-000000000002',
  mission_id: '11111111-1111-1111-1111-111111111111',
  action_type: 'DEPLOYMENT',
  target_resource: 'migrations/0002_add_table.py',
  mission_version: 1,
  decision: 'PENDING',
  signature_digest: 'a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890',
  comment: null,
  responder: null,
  expires_at: new Date(Date.now() + 3600000).toISOString(),
  decided_at: null,
  created_at: new Date().toISOString(),
};

describe('ApprovalsPage Component - Human Delivery Gate', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders pending approval with HMAC signature digest and review gate button', async () => {
    vi.spyOn(apiClient, 'getApprovals').mockResolvedValue([MOCK_APPROVAL]);

    render(<ApprovalsPage />);

    // Verify loading transitions to populated approval
    await waitFor(() => {
      expect(screen.getByText('DEPLOYMENT')).toBeInTheDocument();
    });

    expect(screen.getByText('migrations/0002_add_table.py')).toBeInTheDocument();
    expect(screen.getByText(MOCK_APPROVAL.signature_digest)).toBeInTheDocument();
    expect(screen.getByText('Review Gate')).toBeInTheDocument();
  });

  it('opens review modal and submits approval verdict', async () => {
    vi.spyOn(apiClient, 'getApprovals').mockResolvedValue([MOCK_APPROVAL]);
    const respondSpy = vi.spyOn(apiClient, 'respondApproval').mockResolvedValue({
      ...MOCK_APPROVAL,
      decision: 'APPROVED',
      responder: 'operator@syntra.local',
      comment: 'Verified deployment artifact.',
    });

    render(<ApprovalsPage />);

    await waitFor(() => {
      expect(screen.getByText('Review Gate')).toBeInTheDocument();
    });

    // Click Review Gate
    fireEvent.click(screen.getByText('Review Gate'));

    // Modal should be open
    expect(screen.getByText('Review Approval Ticket: DEPLOYMENT')).toBeInTheDocument();
    expect(screen.getByDisplayValue(MOCK_APPROVAL.signature_digest)).toBeInTheDocument();

    // Fill in justification comment
    const commentInput = screen.getByPlaceholderText(/Reviewed regression test logs/i);
    fireEvent.change(commentInput, { target: { value: 'Verified deployment artifact.' } });

    // Submit Authorize (Approve)
    const submitButton = screen.getByText('Authorize & Approve');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(respondSpy).toHaveBeenCalledWith(MOCK_APPROVAL.id, {
        decision: 'APPROVED',
        digest: MOCK_APPROVAL.signature_digest,
        responder: expect.any(String),
        comment: 'Verified deployment artifact.',
      });
    });
  });
});
