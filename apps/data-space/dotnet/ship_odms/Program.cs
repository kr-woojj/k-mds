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

app.MapStaticAssets();
app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

app.Run();
