from src.ufo_pipeline.advanced import run_advanced_phases
from src.ufo_pipeline.config import RAW_DATA, REPORT
from src.ufo_pipeline.data import convert_types, download_data, load_transmission
from src.ufo_pipeline.features import build_feature_set
from src.ufo_pipeline.labels import describe_hoax_label
from src.ufo_pipeline.modeling import baseline_always_not_hoax_metrics, train_and_evaluate
from src.ufo_pipeline.reporting import render_report, write_report


def main() -> None:
    csv_path = download_data(RAW_DATA)
    load_result = load_transmission(csv_path)
    frame, anomalies = convert_types(load_result.frame)
    label_result = describe_hoax_label(frame["comments"])
    target = label_result.labels

    feature_set = build_feature_set(frame)
    leaky_features = feature_set.frame
    clean_features = feature_set.without_leakage()
    leaky_metrics = train_and_evaluate(leaky_features, target)
    clean_metrics = train_and_evaluate(clean_features, target)
    baseline_metrics = baseline_always_not_hoax_metrics(target)
    advanced = run_advanced_phases(frame, target)

    report = render_report(
        load_result=load_result,
        anomalies=anomalies,
        label_result=label_result,
        leakage_rows=feature_set.leakage_rows,
        leaky_metrics=leaky_metrics,
        clean_metrics=clean_metrics,
        baseline_metrics=baseline_metrics,
        advanced=advanced,
    )
    write_report(REPORT, report)
    print(f"Rapport ecrit dans {REPORT}")


if __name__ == "__main__":
    main()
