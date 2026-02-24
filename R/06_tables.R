###############################################################################
# 06_tables.R
# Generate LaTeX tables for the academic paper
###############################################################################

library(sf)

# Helper: escape LaTeX special characters in text
escape_latex <- function(s) {
  s <- gsub("&", "\\\\&", s)
  s <- gsub("_", "\\\\_", s)
  s <- gsub("%", "\\\\%", s)
  s
}


# Table 1: Distance Decay Parameter (theta) interpretation -------------------

generate_table1_theta <- function() {
  '\\begin{table}[H]
\\centering
\\caption{Distance Decay Parameter Interpretation}
\\label{tab:theta_values}
\\begin{tabular}{@{}ll@{}}
\\toprule
\\textbf{Parameter Value} & \\textbf{Interpretation} \\\\
\\midrule
$\\theta = -0.5$ & Slow decay; long trips acceptable \\\\
$\\theta = -1.0$ & Moderate decay (default) \\\\
$\\theta = -2.0$ & Fast decay; only nearby destinations matter \\\\
$\\theta = -3.0$ & Very fast decay; highly localized trips \\\\
\\bottomrule
\\end{tabular}
\\end{table}
'
}


# Table 2: K-Penalty parameter interpretation --------------------------------

generate_table2_k <- function() {
  '\\begin{table}[H]
\\centering
\\caption{K-Penalty Parameter Interpretation}
\\label{tab:k_values}
\\begin{tabular}{@{}ll@{}}
\\toprule
\\textbf{K Value} & \\textbf{Interpretation} \\\\
\\midrule
$K = 2$ & Mild penalty; cyclists tolerate mixed traffic \\\\
$K = 5$ & Moderate preference (default) \\\\
$K = 10$ & Strong preference for bike lanes \\\\
$K = 50$ & Very strong preference \\\\
$K = 100$ & Near-exclusive use of bike lanes \\\\
\\bottomrule
\\end{tabular}
\\end{table}
'
}


# Table 3: Data Sources ------------------------------------------------------

generate_table3_data_sources <- function() {
  '\\begin{table}[H]
\\centering
\\caption{Data Sources}
\\label{tab:data_sources}
\\begin{tabular}{@{}lll@{}}
\\toprule
\\textbf{Data} & \\textbf{Source} & \\textbf{Description} \\\\
\\midrule
Statistical Areas & JTMP Team & 98 geographic units \\\\
Population & JTMP Team & Residents per area, 2020--2040 \\\\
Employment & JTMP Team & Jobs per area, 2020--2040 \\\\
Completed Bike Lanes & JTMP Team & Existing infrastructure \\\\
Under Construction & JTMP Team & Lanes being built \\\\
Wishing List Lanes & Author & 24 proposed future lanes \\\\
Road Network & OpenStreetMap & Complete road network \\\\
\\bottomrule
\\end{tabular}
\\end{table}
'
}


# Table 4: Wishing List Bike Lanes -------------------------------------------

generate_table4_wishing_list <- function(wishing) {
  wishing_proj <- st_transform(wishing, TARGET_CRS)
  n <- nrow(wishing_proj)

  rows <- character(n)
  for (i in seq_len(n)) {
    name_raw <- wishing_proj$Name[i]
    name_en  <- escape_latex(transliterate(name_raw))
    len_m    <- round(as.numeric(st_length(st_geometry(wishing_proj)[i])))
    rows[i]  <- sprintf("%d & %s & Jerusalem & %s", i, name_en, format(len_m, big.mark = ","))
  }

  paste0(
    '\\begin{table}[H]\n\\centering\n',
    '\\caption{Wishing List Bike Lanes}\n\\label{tab:wishing_list}\n\\small\n',
    '\\begin{tabular}{@{}clll@{}}\n\\toprule\n',
    '\\textbf{ID} & \\textbf{Lane Name} & \\textbf{Location} & \\textbf{Length (m)} \\\\\n',
    '\\midrule\n',
    paste(rows, collapse = " \\\\\n"), " \\\\\n",
    '\\bottomrule\n\\end{tabular}\n\\end{table}\n'
  )
}


# Table 5: Independent Lane Rankings (default parameters) ---------------------

generate_table5_rankings <- function(rankings) {
  # Independent (additive) mode: each lane evaluated against the common baseline.
  # Includes length and improvement-per-km for cost-effectiveness comparison.
  n <- nrow(rankings)
  rows <- character(n)
  for (i in seq_len(n)) {
    name    <- escape_latex(rankings$name[i])
    len_km  <- rankings$length_m[i] / 1000
    pct     <- rankings$improvement_pct[i]
    per_km  <- if (len_km > 0) pct / len_km else 0
    rows[i] <- sprintf("%d & %s & %.1f & %.2f & %.2f",
                       rankings$rank[i], name, len_km, pct, per_km)
  }

  paste0(
    '\\begin{table}[H]\n\\centering\n',
    '\\caption{Independent Lane Rankings -- Each Lane vs.\\ Baseline ($K=5$, $\\theta=-1.0$)}\n',
    '\\label{tab:lane_rankings}\n',
    '\\small\n',
    '\\begin{tabular}{@{}clccc@{}}\n\\toprule\n',
    '\\textbf{Rank} & \\textbf{Lane Name} & \\textbf{Length (km)} & ',
    '\\textbf{\\% Improv.} & \\textbf{\\% per km} \\\\\n',
    '\\midrule\n',
    paste(rows, collapse = " \\\\\n"), " \\\\\n",
    '\\bottomrule\n\\end{tabular}\n\\end{table}\n'
  )
}


# Table 5b: Sequential (Greedy) Lane Rankings ---------------------------------

generate_table5b_sequential <- function(seq_rankings) {
  # Sequential greedy mode: each lane evaluated against the updated baseline
  # that includes all previously selected lanes.
  # Includes length and marginal-per-km for cost-effectiveness comparison.
  n <- nrow(seq_rankings)
  rows <- character(n)
  for (i in seq_len(n)) {
    name   <- escape_latex(seq_rankings$name[i])
    len_km <- seq_rankings$length_m[i] / 1000
    marg   <- seq_rankings$marginal_pct[i]
    per_km <- if (len_km > 0) marg / len_km else 0
    rows[i] <- sprintf("%d & %s & %.1f & %.2f & %.2f & %.2f",
                       seq_rankings$rank[i], name, len_km,
                       marg, per_km,
                       seq_rankings$cumulative_pct[i])
  }

  paste0(
    '\\begin{table}[H]\n\\centering\n',
    '\\caption{Sequential (Greedy) Lane Rankings ($K=5$, $\\theta=-1.0$)}\n',
    '\\label{tab:sequential_rankings}\n',
    '\\small\n',
    '\\begin{tabular}{@{}clcccc@{}}\n\\toprule\n',
    '\\textbf{Step} & \\textbf{Lane Name} & \\textbf{Length (km)} & ',
    '\\textbf{Marginal \\%} & \\textbf{\\% per km} & \\textbf{Cumulative \\%} \\\\\n',
    '\\midrule\n',
    paste(rows, collapse = " \\\\\n"), " \\\\\n",
    '\\bottomrule\n\\end{tabular}\n\\end{table}\n'
  )
}


# Table 5c: Subtractive Lane Rankings -----------------------------------------

generate_table5c_subtractive <- function(sub_rankings) {
  # Subtractive mode: full network (baseline + all wishing-list lanes),
  # remove one lane at a time, measure % loss.
  # Includes loss-per-km for cost-effectiveness comparison.
  n <- nrow(sub_rankings)
  rows <- character(n)
  for (i in seq_len(n)) {
    name    <- escape_latex(sub_rankings$name[i])
    len_km  <- sub_rankings$length_m[i] / 1000
    loss    <- sub_rankings$loss_pct[i]
    per_km  <- if (len_km > 0) loss / len_km else 0
    rows[i] <- sprintf("%d & %s & %.1f & %.2f & %.2f",
                       sub_rankings$rank[i], name, len_km,
                       loss, per_km)
  }

  paste0(
    '\\begin{table}[H]\n\\centering\n',
    '\\caption{Subtractive Lane Rankings -- Full Network Minus One ($K=5$, $\\theta=-1.0$)}\n',
    '\\label{tab:subtractive_rankings}\n',
    '\\small\n',
    '\\begin{tabular}{@{}clccc@{}}\n\\toprule\n',
    '\\textbf{Rank} & \\textbf{Lane Name} & \\textbf{Length (km)} & ',
    '\\textbf{\\% Loss} & \\textbf{\\% per km} \\\\\n',
    '\\midrule\n',
    paste(rows, collapse = " \\\\\n"), " \\\\\n",
    '\\bottomrule\n\\end{tabular}\n\\end{table}\n'
  )
}


# Table 6: Sensitivity to K --------------------------------------------------

generate_table6_sensitivity_k <- function(rankings_by_k,
                                          k_values = c(2, 5, 10, 50, 100)) {
  rows <- character(5)
  for (rank in 1:5) {
    parts <- as.character(rank)
    for (k in k_values) {
      key <- as.character(k)
      df <- rankings_by_k[[key]]
      if (!is.null(df) && nrow(df) >= rank) {
        name <- df$name[df$rank == rank]
        name <- if (nchar(name) > 15) paste0(substr(name, 1, 12), "...") else name
        parts <- c(parts, escape_latex(name))
      } else {
        parts <- c(parts, "--")
      }
    }
    rows[rank] <- paste(parts, collapse = " & ")
  }

  paste0(
    '\\begin{table}[H]\n\\centering\n',
    '\\caption{Top 5 Lane Rankings by K Value}\n\\label{tab:sensitivity_k}\n',
    '\\begin{tabular}{@{}clllll@{}}\n\\toprule\n',
    '\\textbf{Rank} & \\textbf{K=2} & \\textbf{K=5} & \\textbf{K=10} & \\textbf{K=50} & \\textbf{K=100} \\\\\n',
    '\\midrule\n',
    paste(rows, collapse = " \\\\\n"), " \\\\\n",
    '\\bottomrule\n\\end{tabular}\n\\end{table}\n'
  )
}


# Table 7: Sensitivity to theta ----------------------------------------------

generate_table7_sensitivity_theta <- function(rankings_by_theta,
                                              theta_values = c(-0.5, -1.0, -1.5, -2.0, -3.0)) {
  rows <- character(5)
  for (rank in 1:5) {
    parts <- as.character(rank)
    for (theta in theta_values) {
      key <- as.character(theta)
      df <- rankings_by_theta[[key]]
      if (!is.null(df) && nrow(df) >= rank) {
        name <- df$name[df$rank == rank]
        name <- if (nchar(name) > 12) paste0(substr(name, 1, 10), "...") else name
        parts <- c(parts, escape_latex(name))
      } else {
        parts <- c(parts, "--")
      }
    }
    rows[rank] <- paste(parts, collapse = " & ")
  }

  paste0(
    '\\begin{table}[H]\n\\centering\n',
    '\\caption{Top 5 Lane Rankings by $\\theta$ Value}\n\\label{tab:sensitivity_theta}\n',
    '\\begin{tabular}{@{}clllll@{}}\n\\toprule\n',
    '\\textbf{Rank} & $\\theta=-0.5$ & $\\theta=-1.0$ & $\\theta=-1.5$ & $\\theta=-2.0$ & $\\theta=-3.0$ \\\\\n',
    '\\midrule\n',
    paste(rows, collapse = " \\\\\n"), " \\\\\n",
    '\\bottomrule\n\\end{tabular}\n\\end{table}\n'
  )
}


# Table 8: Temporal analysis (rankings by year) ------------------------------

generate_table8_temporal <- function(rankings_by_year,
                                     years = c(2020, 2025, 2030, 2035, 2040)) {
  rows <- character(5)
  for (rank in 1:5) {
    parts <- as.character(rank)
    for (yr in years) {
      key <- as.character(yr)
      df <- rankings_by_year[[key]]
      if (!is.null(df) && nrow(df) >= rank) {
        name <- df$name[df$rank == rank]
        name <- if (nchar(name) > 12) paste0(substr(name, 1, 10), "...") else name
        parts <- c(parts, escape_latex(name))
      } else {
        parts <- c(parts, "--")
      }
    }
    rows[rank] <- paste(parts, collapse = " & ")
  }

  paste0(
    '\\begin{table}[H]\n\\centering\n',
    '\\caption{Top 5 Rankings by Year}\n\\label{tab:temporal}\n',
    '\\begin{tabular}{@{}clllll@{}}\n\\toprule\n',
    '\\textbf{Rank} & \\textbf{2020} & \\textbf{2025} & \\textbf{2030} & \\textbf{2035} & \\textbf{2040} \\\\\n',
    '\\midrule\n',
    paste(rows, collapse = " \\\\\n"), " \\\\\n",
    '\\bottomrule\n\\end{tabular}\n\\end{table}\n'
  )
}


# Table 9: Implementation phases ---------------------------------------------

generate_table9_phases <- function(seq_rankings) {
  # Use sequential (greedy) rankings so cumulative column is meaningful.
  n <- nrow(seq_rankings)
  phase_ends <- c(3, 6, 9, 12)

  rows <- character(0)
  for (p in seq_along(phase_ends)) {
    end_idx <- min(phase_ends[p], n)
    cum_pct <- seq_rankings$cumulative_pct[end_idx]

    if (p == 1) {
      names_str <- paste(seq_rankings$name[1:end_idx], collapse = ", ")
      label <- "Phase 1 (Top 3)"
    } else {
      start_idx <- phase_ends[p - 1] + 1
      if (start_idx > n) next
      names_str <- paste0("+ ", paste(seq_rankings$name[start_idx:end_idx], collapse = ", "))
      label <- sprintf("Phase %d (+3)", p)
    }
    names_str <- escape_latex(substr(names_str, 1, 50))
    rows <- c(rows, sprintf("%s & %s & %.2f", label, names_str, cum_pct))
  }

  # Complete row
  total_pct <- seq_rankings$cumulative_pct[n]
  rows <- c(rows, sprintf("Complete (All %d) & All proposed lanes & %.2f", n, total_pct))

  paste0(
    '\\begin{table}[H]\n\\centering\n',
    '\\caption{Cumulative Accessibility Improvement by Implementation Phase}\n',
    '\\label{tab:phases}\n',
    '\\begin{tabular}{@{}llc@{}}\n\\toprule\n',
    '\\textbf{Phase} & \\textbf{Lanes Added} & \\textbf{Cumulative \\%} \\\\\n',
    '\\midrule\n',
    paste(rows, collapse = " \\\\\n"), " \\\\\n",
    '\\bottomrule\n\\end{tabular}\n\\end{table}\n'
  )
}


# Table 10: Computational performance ----------------------------------------

generate_table10_performance <- function() {
  '\\begin{table}[H]
\\centering
\\caption{Computational Performance}
\\label{tab:performance}
\\begin{tabular}{@{}ll@{}}
\\toprule
\\textbf{Operation} & \\textbf{Runtime} \\\\
\\midrule
Network construction & 15--30 seconds \\\\
Single accessibility calculation & 30--60 seconds \\\\
Lane ranking (25 lanes) & 10--15 minutes \\\\
Path finding (single pair) & $<$100 milliseconds \\\\
\\bottomrule
\\end{tabular}
\\end{table}
'
}


# Table 11: Network statistics -----------------------------------------------

generate_table11_network_stats <- function(G, n_areas) {
  paste0(
    '\\begin{table}[H]\n\\centering\n',
    '\\caption{Network Statistics}\n\\label{tab:network_stats}\n',
    '\\begin{tabular}{@{}ll@{}}\n\\toprule\n',
    '\\textbf{Metric} & \\textbf{Value} \\\\\n\\midrule\n',
    sprintf("Total nodes & %s \\\\\n", format(vcount(G), big.mark = ",")),
    sprintf("Total edges & %s \\\\\n", format(ecount(G), big.mark = ",")),
    sprintf("Statistical areas & %d \\\\\n", n_areas),
    "Node merge tolerance & 15 meters \\\\\n",
    "Gap connection threshold & 50 meters \\\\\n",
    '\\bottomrule\n\\end{tabular}\n\\end{table}\n'
  )
}


# --- Write all tables to files -----------------------------------------------

write_table <- function(content, filepath) {
  writeLines(content, filepath)
  message("  Saved ", filepath)
}
