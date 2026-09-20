import React from "react";
import { useApiList } from "../../hooks/useApiList";
import { FocConsumerTypeTable } from "../../components/domain/FocConsumerTypeTable";

export const FocConsumerTypePage: React.FC = () => {
  const { data, loading, error } = useApiList(`/foc-consumer-types`);
  return (
    <div>
      <h2>FOC 소비자 종류</h2>
      <FocConsumerTypeTable items={data} loading={loading} error={error} />
      {error && <div className="api-error-banner">API 서버에 연결할 수 없습니다.</div>}
    </div>
  );
};
