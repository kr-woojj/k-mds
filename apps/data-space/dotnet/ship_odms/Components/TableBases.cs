using Microsoft.AspNetCore.Components;
using System.Collections.Generic;
using ship_odms.Models;

namespace ship_odms.Components
{
    public class ApiErrorBannerBase : ComponentBase
    {
        [Parameter] public string? ErrorMessage { get; set; }
    }

    public class CargoOnboardTableBase : ComponentBase
    {
        [Parameter] public List<CargoOnboard>? Items { get; set; }
        [Parameter] public bool Loading { get; set; }
        [Parameter] public string? Error { get; set; }
        [Parameter] public EventCallback<CargoOnboard> OnRowClick { get; set; }
    }

    public class ElectricConsumptionTableBase : ComponentBase
    {
        [Parameter] public List<ElectricConsumption>? Items { get; set; }
        [Parameter] public bool Loading { get; set; }
        [Parameter] public string? Error { get; set; }
        [Parameter] public EventCallback<ElectricConsumption> OnRowClick { get; set; }
    }

    public class FocConsumerTypeTableBase : ComponentBase
    {
        [Parameter] public List<FocConsumerType>? Items { get; set; }
        [Parameter] public bool Loading { get; set; }
        [Parameter] public string? Error { get; set; }
        [Parameter] public EventCallback<FocConsumerType> OnRowClick { get; set; }
    }

    public class FuelConsumptionTableBase : ComponentBase
    {
        [Parameter] public List<FuelConsumption>? Items { get; set; }
        [Parameter] public bool Loading { get; set; }
        [Parameter] public string? Error { get; set; }
        [Parameter] public EventCallback<FuelConsumption> OnRowClick { get; set; }
    }

    public class FocFuelTypeTableBase : ComponentBase
    {
        [Parameter] public List<FocFuelType>? Items { get; set; }
        [Parameter] public bool Loading { get; set; }
        [Parameter] public string? Error { get; set; }
        [Parameter] public EventCallback<FocFuelType> OnRowClick { get; set; }
    }

    public class MeasuredCarbonDioxideTableBase : ComponentBase
    {
        [Parameter] public List<MeasuredCarbonDioxide>? Items { get; set; }
        [Parameter] public bool Loading { get; set; }
        [Parameter] public string? Error { get; set; }
        [Parameter] public EventCallback<MeasuredCarbonDioxide> OnRowClick { get; set; }
    }

    public class PerformanceReportTableBase : ComponentBase
    {
        [Parameter] public List<PerformanceReport>? Items { get; set; }
        [Parameter] public bool Loading { get; set; }
        [Parameter] public string? Error { get; set; }
        [Parameter] public EventCallback<PerformanceReport> OnRowClick { get; set; }
    }

    public class PortCallTableBase : ComponentBase
    {
        [Parameter] public List<PortCall>? Items { get; set; }
        [Parameter] public bool Loading { get; set; }
        [Parameter] public string? Error { get; set; }
        [Parameter] public EventCallback<PortCall> OnRowClick { get; set; }
    }

    public class ShipTableBase : ComponentBase
    {
        [Parameter] public List<Ship>? Items { get; set; }
        [Parameter] public bool Loading { get; set; }
        [Parameter] public string? Error { get; set; }
        [Parameter] public EventCallback<Ship> OnRowClick { get; set; }
    }

    public class VoyageTableBase : ComponentBase
    {
        [Parameter] public List<Voyage>? Items { get; set; }
        [Parameter] public bool Loading { get; set; }
        [Parameter] public string? Error { get; set; }
        [Parameter] public EventCallback<Voyage> OnRowClick { get; set; }
    }

    public class WeatherDetailsTableBase : ComponentBase
    {
        [Parameter] public List<WeatherDetails>? Items { get; set; }
        [Parameter] public bool Loading { get; set; }
        [Parameter] public string? Error { get; set; }
        [Parameter] public EventCallback<WeatherDetails> OnRowClick { get; set; }
    }

    public class YearPerformanceReportTableBase : ComponentBase
    {
        [Parameter] public List<YearPerformanceReport>? Items { get; set; }
        [Parameter] public bool Loading { get; set; }
        [Parameter] public string? Error { get; set; }
        [Parameter] public EventCallback<YearPerformanceReport> OnRowClick { get; set; }
    }
}
