using ship_odms.Services;
using ship_odms.Components;


var builder = WebApplication.CreateBuilder(args);

// 명시적으로 Kestrel 포트 8088 지정
builder.WebHost.ConfigureKestrel(options =>
{
    options.ListenAnyIP(8088);
});


// Add services to the container.
builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents();


builder.Services.AddScoped(sp => new HttpClient { BaseAddress = new Uri("http://localhost:8088/") });
// ApiClient에 HttpClient를 명확히 주입 (BaseAddress는 ApiClient에서 설정)
builder.Services.AddScoped<ApiClient>();

// 환경 변수에서 API BaseUrl을 읽어 HttpClient BaseAddress로 사용
var apiBaseUrl = Environment.GetEnvironmentVariable("ApiSettings__BaseUrl") ?? "http://localhost:8088/api";
builder.Services.AddScoped(sp => new HttpClient { BaseAddress = new Uri(apiBaseUrl.EndsWith("/") ? apiBaseUrl : apiBaseUrl + "/") });
builder.Services.AddScoped<ApiClient>();

var app = builder.Build();

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
    // The default HSTS value is 30 days. You may want to change this for production scenarios, see https://aka.ms/aspnetcore-hsts.
    app.UseHsts();
}
app.UseStatusCodePagesWithReExecute("/not-found");
app.UseHttpsRedirection();

app.UseAntiforgery();

// 내려받기 중계: 브라우저가 백엔드·하네스 주소를 몰라도 포털 주소로 파일을 받는다 (2026-11-17).
var harnessUrl = (app.Configuration["Portal:HarnessUrl"] ?? "http://localhost:8090").TrimEnd('/');
app.MapGet("/export/ships/{id:int}", async (int id, string? format, HttpClient http) =>
{
    var csv = format == "csv";
    using var res = await http.GetAsync($"ships/{id}/export?format={(csv ? "csv" : "json")}");
    if (!res.IsSuccessStatusCode) return Results.StatusCode((int)res.StatusCode);
    return Results.File(await res.Content.ReadAsByteArrayAsync(), csv ? "application/zip" : "application/json", $"ship-{id}-export.{(csv ? "zip" : "json")}");
});
app.MapGet("/export/consistency/{runId:regex(^run_[0-9]+$)}", async (string runId, HttpClient http) =>
{
    using var res = await http.GetAsync($"{harnessUrl}/runs/{runId}/consistency.csv");
    if (!res.IsSuccessStatusCode) return Results.StatusCode((int)res.StatusCode);
    return Results.File(await res.Content.ReadAsByteArrayAsync(), "text/csv; charset=utf-8", $"{runId}-consistency-checks.csv");
});

app.MapStaticAssets();
app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

app.Run();
