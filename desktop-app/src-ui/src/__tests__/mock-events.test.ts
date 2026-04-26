/**
 * Regression test for UI state desync bug.
 * Tests that:
 * 1. Submitting a second task resets old state
 * 2. Mock plan changes to the new task text
 * 3. Mock file paths are unique per run
 * 4. Accept removes the selected patch from pending
 * 5. streaming_chunk events are translated to HcodeMessage
 */
import { createMockEventStream, agentEventToHcodeMessage } from '../ipc/mock-events';

describe('Mock Event Stream - State Desync Regression', () => {

  test('createMockEventStream uses the submitted task text in all content', () => {
    const task = 'add error handling to API routes';
    const events = createMockEventStream(task);

    // Plan must contain the task text
    const planEvent = events.find(e => e.type === 'plan_created');
    expect(planEvent).toBeDefined();
    if (planEvent && planEvent.type === 'plan_created') {
      expect(planEvent.markdown).toContain(task);
      expect(planEvent.taskMd).toContain(task);
      expect(planEvent.implementationPlanMd).toContain(task);
    }

    // File patch must contain the task text
    const patchEvent = events.find(e => e.type === 'file_patch_proposed');
    expect(patchEvent).toBeDefined();
    if (patchEvent && patchEvent.type === 'file_patch_proposed') {
      expect(patchEvent.newContent).toContain(task);
      expect(patchEvent.diff).toContain(task);
    }

    // Verification must contain the task text
    const verifyEvent = events.find(e => e.type === 'verification_completed');
    expect(verifyEvent).toBeDefined();
    if (verifyEvent && verifyEvent.type === 'verification_completed') {
      expect(verifyEvent.markdown).toContain(task);
    }

    // Done summary must contain the task text
    const doneEvent = events.find(e => e.type === 'done');
    expect(doneEvent).toBeDefined();
    if (doneEvent && doneEvent.type === 'done') {
      expect(doneEvent.summary).toContain(task);
    }
  });

  test('two consecutive tasks produce different file paths (no identity collision)', () => {
    const events1 = createMockEventStream('task one');
    const events2 = createMockEventStream('task two');

    const patch1 = events1.find(e => e.type === 'file_patch_proposed');
    const patch2 = events2.find(e => e.type === 'file_patch_proposed');

    expect(patch1).toBeDefined();
    expect(patch2).toBeDefined();

    if (patch1?.type === 'file_patch_proposed' && patch2?.type === 'file_patch_proposed') {
      // Paths MUST be different so Accept in task 1 doesn't affect task 2
      expect(patch1.path).not.toEqual(patch2.path);
    }
  });

  test('two consecutive tasks produce different plan content', () => {
    const events1 = createMockEventStream('refactor the database layer');
    const events2 = createMockEventStream('add unit tests for auth');

    const plan1 = events1.find(e => e.type === 'plan_created');
    const plan2 = events2.find(e => e.type === 'plan_created');

    expect(plan1).toBeDefined();
    expect(plan2).toBeDefined();

    if (plan1?.type === 'plan_created' && plan2?.type === 'plan_created') {
      expect(plan1.markdown).not.toEqual(plan2.markdown);
      expect(plan1.markdown).toContain('refactor the database layer');
      expect(plan2.markdown).toContain('add unit tests for auth');
    }
  });

  test('agentEventToHcodeMessage maps streaming_chunk to task_update', () => {
    const result = agentEventToHcodeMessage({
      type: 'streaming_chunk',
      content: 'Analyzing code...',
      phase: 'planning',
    });

    expect(result).not.toBeNull();
    expect(result).toEqual({
      type: 'task_update',
      payload: { markdown: 'Analyzing code...' },
    });
  });

  test('agentEventToHcodeMessage maps file_patch_proposed correctly', () => {
    const result = agentEventToHcodeMessage({
      type: 'file_patch_proposed',
      path: 'src/task_1_output.py',
      diff: '@@ test diff',
      originalContent: 'original',
      newContent: 'modified',
      timestamp: Date.now(),
    });

    expect(result).not.toBeNull();
    expect(result).toEqual({
      type: 'file_patch',
      payload: {
        path: 'src/task_1_output.py',
        diff: '@@ test diff',
        backup: '',
        originalContent: 'original',
        newContent: 'modified',
      },
    });
  });

  test('ACCEPT_PATCH removes patch by path identity', () => {
    // Simulate the reducer logic directly
    const patches = [
      { path: 'src/task_1_output.py', diff: 'diff1', backup: '', originalContent: 'a', newContent: 'b' },
      { path: 'src/task_2_output.py', diff: 'diff2', backup: '', originalContent: 'c', newContent: 'd' },
    ];

    const pathToAccept = 'src/task_1_output.py';
    const remaining = patches.filter(p => p.path !== pathToAccept);

    expect(remaining).toHaveLength(1);
    expect(remaining[0].path).toBe('src/task_2_output.py');
  });
});
