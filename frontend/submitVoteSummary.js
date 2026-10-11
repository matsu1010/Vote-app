import { getLocalVote, clearLocalVotes } from "./localVoteStore.js";

export async function submitVoteSummary(questionId, token) {
  const localVote = getLocalVote(questionId);

  if (!localVote) {
    throw new Error("No local vote found for this question");
  }

  const payload = {
    question_id: questionId,
    answer: localVote.answer,
    source: "local-device"
  };

  const response = await fetch(`/api/results/question/${questionId}/forward`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`Submit failed: ${response.status}`);
  }

  const result = await response.json();
  clearLocalVotes();
  return result;
}
