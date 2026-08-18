$pdf_mode = 1;
$pdflatex = 'pdflatex -shell-escape -interaction=nonstopmode %O %S';
$biber = 'biber %O %S';
$makeglossaries = 'makeglossaries %O %S';
@generated_exts = (@generated_exts, 'glo', 'gls', 'glg');
add_cus_dep('glo', 'gls', 0, 'run_makeglossaries');
add_cus_dep('acn', 'acr', 0, 'run_makeglossaries');

sub run_makeglossaries {
    my ($base_name, $path) = fileparse( $_[0] );
    pushd $path;
    my $return = system "makeglossaries", $base_name;
    popd;
    return $return;
}
