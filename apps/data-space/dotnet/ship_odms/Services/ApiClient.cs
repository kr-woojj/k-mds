// API 클라이언트 서비스: React의 api/client.js를 Blazor/.NET용으로 이식
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using System;
using System.Collections.Generic;
using ship_odms.Models;

namespace ship_odms.Services
{
    public class ApiClient
    {
        private readonly HttpClient _httpClient;

        public ApiClient(HttpClient httpClient)
        {
            _httpClient = httpClient;
            // BaseAddress는 Program.cs에서 환경 변수로 주입됨
        }

        public async Task<T?> GetAsync<T>(string path)
        {
            var response = await _httpClient.GetAsync(path);
            if (!response.IsSuccessStatusCode)
            {
                var error = await response.Content.ReadAsStringAsync();
                throw new Exception($"API Error: {error}");
            }
            if (response.StatusCode == System.Net.HttpStatusCode.NoContent)
                return default;
            var options = new System.Text.Json.JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true,
                MaxDepth = 128,
                IgnoreReadOnlyProperties = true,
                DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull
            };

            // 순환 참조 우회: report 필드 제거
            var json = await response.Content.ReadAsStringAsync();
            using var doc = System.Text.Json.JsonDocument.Parse(json);
            var root = doc.RootElement;
            if (root.ValueKind == System.Text.Json.JsonValueKind.Array)
            {
                var arr = new List<System.Text.Json.JsonElement>();
                foreach (var item in root.EnumerateArray())
                {
                    using var objDoc = System.Text.Json.JsonDocument.Parse(RemoveReportFields(item.GetRawText()));
                    arr.Add(objDoc.RootElement.Clone());
                }
                var filteredJson = System.Text.Json.JsonSerializer.Serialize(arr);
                return System.Text.Json.JsonSerializer.Deserialize<T?>(filteredJson, options);
            }
            else
            {
                var filteredJson = RemoveReportFields(json);
                return System.Text.Json.JsonSerializer.Deserialize<T?>(filteredJson, options);
            }

            // 하위 report 필드 제거 함수
            static string RemoveReportFields(string json)
            {
                using var doc = System.Text.Json.JsonDocument.Parse(json);
                var root = doc.RootElement;
                if (root.ValueKind != System.Text.Json.JsonValueKind.Object)
                    return json;
                var dict = new Dictionary<string, object?>();
                foreach (var prop in root.EnumerateObject())
                {
                    if (prop.NameEquals("electricConsumption") || prop.NameEquals("cargoOnboard") || prop.NameEquals("weatherDetails") || prop.NameEquals("fuelConsumption") || prop.NameEquals("measuredCarbonDioxide"))
                    {
                        if (prop.Value.ValueKind == System.Text.Json.JsonValueKind.Array)
                        {
                            var arr = new List<Dictionary<string, object?>>();
                            foreach (var sub in prop.Value.EnumerateArray())
                            {
                                var subDict = new Dictionary<string, object?>();
                                foreach (var subProp in sub.EnumerateObject())
                                {
                                    if (subProp.NameEquals("report") || subProp.NameEquals("fuelConsumption"))
                                        continue;
                                    subDict[subProp.Name] = ConvertJsonElement(subProp.Value);
                                }
                                arr.Add(subDict);
                            }
                            dict[prop.Name] = arr;
                        }
                        else
                        {
                            dict[prop.Name] = ConvertJsonElement(prop.Value);
                        }
                    }
                    else
                    {
                        dict[prop.Name] = ConvertJsonElement(prop.Value);
                    }
                }
                return System.Text.Json.JsonSerializer.Serialize(dict);

                // 내부 함수: JsonElement를 .NET 타입으로 변환
                object? ConvertJsonElement(System.Text.Json.JsonElement element)
                {
                    switch (element.ValueKind)
                    {
                        case System.Text.Json.JsonValueKind.Number:
                            if (element.TryGetInt32(out int i)) return i;
                            if (element.TryGetInt64(out long l)) return l;
                            if (element.TryGetDouble(out double d)) return d;
                            return element.GetRawText();
                        case System.Text.Json.JsonValueKind.String:
                            return element.GetString();
                        case System.Text.Json.JsonValueKind.True:
                        case System.Text.Json.JsonValueKind.False:
                            return element.GetBoolean();
                        case System.Text.Json.JsonValueKind.Null:
                            return null;
                        case System.Text.Json.JsonValueKind.Object:
                            var objDict = new Dictionary<string, object?>();
                            foreach (var p in element.EnumerateObject())
                                objDict[p.Name] = ConvertJsonElement(p.Value);
                            return objDict;
                        case System.Text.Json.JsonValueKind.Array:
                            var list = new List<object?>();
                            foreach (var item in element.EnumerateArray())
                                list.Add(ConvertJsonElement(item));
                            return list;
                        default:
                            return element.GetRawText();
                    }
                }
            }
        }

        public async Task<T?> PostAsync<T>(string path, object body)
        {
            var response = await _httpClient.PostAsJsonAsync(path, body);
            if (!response.IsSuccessStatusCode)
            {
                var error = await response.Content.ReadAsStringAsync();
                throw new Exception($"API Error: {error}");
            }
            return await response.Content.ReadFromJsonAsync<T?>();
        }

        // 필요시 Put, Delete 등 추가 구현
    }
}
