import { useState, useEffect } from "react";
import { apiRequest } from "../api/client";

export function useApiList(path) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError("");
    apiRequest(path)
      .then((res) => {
        if (mounted) setData(res);
      })
      .catch((e) => {
        if (mounted) setError(e.message || "API 연결 오류");
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [path]);

  return { data, loading, error };
}
