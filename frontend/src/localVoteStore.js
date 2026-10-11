const STORAGE_KEY = "vote_app_local_votes_v1";

export function getLocalVotes() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (error) {
    return [];
  }
}

export function saveLocalVote(questionId, answer, extra = {}) {
  const votes = getLocalVotes();
  const existingIndex = votes.findIndex(v => v.questionId === questionId);

  const payload = {
    questionId,
    answer,
    createdAt: new Date().toISOString(),
    ...extra
  };

  if (existingIndex >= 0) {
    votes[existingIndex] = payload;
  } else {
    votes.push(payload);
  }

  localStorage.setItem(STORAGE_KEY, JSON.stringify(votes));
  return payload;
}

export function getLocalVote(questionId) {
  return getLocalVotes().find(v => v.questionId === questionId) || null;
}

export function removeLocalVote(questionId) {
  const votes = getLocalVotes().filter(v => v.questionId !== questionId);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(votes));
}

export function clearLocalVotes() {
  localStorage.removeItem(STORAGE_KEY);
}
