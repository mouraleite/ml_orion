"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { canConsolidacaoMldu, HoldingScope } from "@/lib/consolidacaoMldu";

export function useHoldingMldu(scope: HoldingScope) {
  const { user } = useAuth();
  const storageKey = `holding_mldu_${scope}`;
  const canUseHoldingMldu = canConsolidacaoMldu(user, scope);
  const [holdingMldu, setHoldingMlduState] = useState(false);

  useEffect(() => {
    if (!canUseHoldingMldu) {
      setHoldingMlduState(false);
      return;
    }
    const stored = localStorage.getItem(storageKey);
    setHoldingMlduState(stored === "true");
  }, [canUseHoldingMldu, storageKey]);

  const setHoldingMldu = useCallback(
    (value: boolean) => {
      if (!canUseHoldingMldu) return;
      localStorage.setItem(storageKey, String(value));
      setHoldingMlduState(value);
    },
    [canUseHoldingMldu, storageKey],
  );

  return {
    holdingMldu: canUseHoldingMldu && holdingMldu,
    setHoldingMldu,
    canUseHoldingMldu,
  };
}
