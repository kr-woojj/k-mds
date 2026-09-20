import React from "react";
import { useApiList } from "../../hooks/useApiList";
import { FocFuelTypeTable } from "../../components/domain/FocFuelTypeTable";

export const FocFuelTypePage: React.FC = () => {
  const { data, loading, error } = useApiList(`/foc-fuel-types`);
  return (
    <div>
      <h2>FOC 연료유 종류</h2>
      <FocFuelTypeTable items={data} loading={loading} error={error} />
      {error && <div className="api-error-banner">API 서버에 연결할 수 없습니다.</div>}
    </div>
  );
};
